#  Copyright (C) 2014 Alex Wilson
#  Copyright (C) 2012-14 Abram Hindle
#  
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.


import json, os


from config import Config
from databases import BulkOps, ElasticSearch
from topics_controller import *
import lda

import common, project, task_queue


class LDALoader(TopicsLoader):
    def __init__(self, run, topic_count=100, docs=None):
        self.run = run
        self.client = self.run.client
        self.docs = docs or self.client.get_all_docs()
        super(LDALoader, self).__init__(self.run
                ,all_ids=self.docs.keys()
                ,topics=range(topic_count))

        self.topic_count = topic_count
        self.ids = None # later, we assign to this the ids that we analyze

    @staticmethod
    def create_loader_for_inference(run):
        '''creates a loader for a project, with the topic_count
            deduced from the data already created'''
        topic_count = TopicsController(run.client).count_topics()
        return LDALoader(run, topic_count)

    def compute_lda(self):
        # guards against missing docs
        assert self.docs != None
        self.ids = self.all_ids
        self.lda_model, self.token_counts = \
            lda.LDA.create_from_docs(self.docs, self.ids)
        # This dumps the documents, because we need the memory, it also means the objects cannot recompute lda
        self.docs = None
        self.run.dump_token_ids(self.lda_model.token_ids)
        self.run.dump_bug_ids(self.all_ids)
        self.vw = lda.VowpalWabbit(self.run, self.lda_model,
                                    topic_count=self.topic_count)
        self.vw.make_lda_input(self.token_counts, self.ids)

        self.vw.clean_files()
        common.run_command(self.vw.lda_command())

    def compute_lda_inference(self):
        self.lda_model, analyzed_doc_ids = \
            self.run.load_lda_model_for_inference()

        bug_db = self.client.connect_to_db()

        self.ids = [id for id in self.all_ids if id not in analyzed_doc_ids]
        token_counts = [self.lda_model.convert_and_filter_token_counts(
                        self.lda_model.add_doc_for_inference(doc))
                        for id, doc in bug_db.mget(self.ids)]

        self.vw = lda.VowpalWabbit(self.run, self.lda_model,
                topic_count=self.topic_count)
        self.vw.make_lda_input(token_counts, self.ids)

        self.vw.clean_files_for_inference()
        common.run_command(self.vw.lda_inference_command())

    def update_summaries_in_database(self):
        topics_db = self.client.connect_to_topics_db()
        self.vw.inform_loader(self)
        summary = self.vw.create_summary()

        print 'saving report'
        reports_db = self.client.connect_to_generated_db()
        report = summary.make_report_doc(self.project)
        reports_db[report['doc_id']] = report

        print 'update summaries in database'
        super(LDALoader, self).update_summaries_in_database(self.client)

        updater = BulkOps(self.client, ElasticSearch.TOPICS)

        # TODO: what if there are custom topics before we do LDA
        print "Saving Summaries"
        for i in range(0, len(summary.topic_summaries)):
            updater.update(str(i), {
                'method': 'lda'
                ,'topic_id': i
                ,'words': ' '.join(summary.topic_summaries[i])
            })
            if (i > 0 and i % 50 == 0):
                print 'Committing documents %s' % i
                updater.apply()

        print 'LDA bulk update'
        updater.apply()

        return summary


class LDARun(TopicsRun):
    def __init__(self, project, client=None):
        if client is None:
            client = ElasticSearch(project)
        self.project = project
        self.client = client

        config = Config.getInstance()
        workdir =  config.workdir_path('out')
        #print workdir
        os.system('mkdir -p {}'.format(workdir))

        def wd(path):
            return config.workdir_path('out', path.format(project))
        self.BUG_IDS_DUMP_FILE = wd("{}-bug-ids.json")
        self.TOKEN_DUMP_FILE = wd("{}-token-ids.json")
        self.LDA_INPUT_FNAME = wd("{}-vr_lda_input.lda.txt")
        self.LDA_ID_INPUT_FNAME = wd("{}-vr_lda_input.id.txt")
        self.LDA_WORDS_INPUT_FNAME = wd("{}-vr_lda_input.words.txt")
        self.LDA_PREDICTIONS_FNAME = wd("{}-predictions.dat")
        self.LDA_TOPICS_FNAME = wd("{}-topics.dat")
        self.LDA_CACHE_FILE = wd("{}-topics.dat.cache")

    def load_token_ids(self):
        if not os.path.exists(self.TOKEN_DUMP_FILE):
            return []
        with open(self.TOKEN_DUMP_FILE) as f:
            return json.load(f)

    def dump_token_ids(self, ids):
        with open(self.TOKEN_DUMP_FILE, 'w') as f:
            return json.dump(ids, f, indent=2)

    def load_bug_ids(self):
        if not os.path.exists(self.BUG_IDS_DUMP_FILE):
            return []
        with open(self.BUG_IDS_DUMP_FILE) as f:
            return json.load(f)

    def dump_bug_ids(self, ids):
        with open(self.BUG_IDS_DUMP_FILE, 'w') as f:
            return json.dump(ids, f, indent=2)

    def load_lda_model_for_inference(self):
        '''creates an LDA instance for inference. It has the
            token ids from previously analyzed documents.

            returns lda_model, analyzed_doc_ids
                where analyzed_doc_ids is a set of previously analyzed docs'
                    ids
        '''
        lda_model = lda.LDA()
        lda_model.load_token_ids(self.load_token_ids())
        analyzed_doc_ids = set(self.load_bug_ids())

        return lda_model, analyzed_doc_ids




# tasks for task_queue

class LDATask(task_queue.Task):
    recoverable = True

    def __init__(self, project, topic_count):
        self.topic_count = topic_count
        self.project = project

    def run(self, worker=None, client=None):
        run = LDARun(self.project, client)
        loader = LDALoader(run, self.topic_count)
        loader.compute_lda()
        summaries = loader.update_summaries_in_database()
        project.Project(self.project, client).update_timestamps([
                project.Project.TOPICS_TIMESTAMP,
                project.Project.TOPIC_SCORES_TIMESTAMP])

        return loader, summaries

    def __repr__(self):
        return "LDATASK {} : {}".format(self.project, str(self.topic_count))

    @staticmethod
    def recover(data):
        return LDATask(data['project'], data['topic_count'])


class LDAIncrementalTask(task_queue.Task):
    recoverable = True

    def __init__(self, project):
        self.project = project

    def run(self, worker=None, client=None):
        run = LDARun(self.project, client)
        loader = LDALoader.create_loader_for_inference(run)
        loader.compute_lda_inference()
        summaries = loader.update_summaries_in_database()
        project.Project(self.project, client).update_timestamps([
                            project.Project.TOPIC_SCORES_TIMESTAMP])
        return loader, summaries

    @staticmethod
    def recover(data):
        return LDAIncrementalTask(data['project'])



if __name__ ==  '__main__':
    import argparse
    parser = argparse.ArgumentParser('LDA analyser')
    parser.add_argument('project', help='project name')
    parser.add_argument('--topics', type=int, default=100,
        help='number of topics to generate (no effect on incremental)')
    parser.add_argument('--incremental', help='do an incremental analysis')

    Config.add_args(parser)
    args = parser.parse_args()
    config = Config.build(args)

    if args.incremental:
        LDAIncrementalTask(args.project).run()
    else:
        print 'running LDA analysis on {} with {} topics'.format(
                args.project, args.topics)
        LDATask(args.project, args.topics).run()
