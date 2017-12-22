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


import base64, itertools, io, json, math, os, re, tarfile, uuid
import nltk
from nltk import RegexpTokenizer
from dateutil.tz import tzutc


import datetime

def utc_now():
    '''returns a timezone-aware datetime object for the current time'''
    return datetime.datetime.utcnow().replace(tzinfo=tzutc())



# utility functions

def d2s(v):
    if (v == {}):
        return ""
    return v

def d2sblank(doc, key):
    return d2s(doc.get(key,""))

def as_list(v):
    if (v.__class__ == [].__class__):
        return v
    return [v]

def sorted_indices(x, reverse=False):
    indices = range(0,len(x))
    indices.sort(key = lambda i: x[i], reverse=reverse)
    return indices

def reverse_dict(d):
    return dict((v,k) for k, v in d.iteritems())

def compact_cosine( dtm, ids, topn = 50 ):
    ''' 
    This function makes a reduced cosine distance, it uses more computation
    but should stay in memory 
    '''
    out = {}
    for i in range(0, len(dtm)):
        l = scipy.spatial.distance.cdist( dtm[i:i+1], dtm[0:], 'cosine' )
        v = l[0]
        indices = sorted_indices(v)[0:topn]
        ol = [{"id":ids[ind],"i":ind,"r":v[ind]} for ind in indices]
        out[ids[i]] = ol
    return out

class LDA(object):
    STOP_WORDS_PATH = 'stop_words'
    STOP_WORDS_PATTERN = re.compile("^[a-zA-Z0-9\\._\\/\\\\]+$", re.I)

    DEFAULT_TOKENIZER = RegexpTokenizer(r'\w+')

    def __init__(self, tokenizer=DEFAULT_TOKENIZER,
            stop_words_path=STOP_WORDS_PATH):
        self.tokenizer = tokenizer
        self.stopwords = self.read_stop_words(stop_words_path)

        self.token_ids = {}
        self.next_token_id = 0
        self.docs_per_token = {}
        self.doc_count = 0

    def load_token_ids(self, token_ids):
        self.token_ids = token_ids
        self.next_token_id = max(token_ids.values()) + 1
        # note: docs_per_token is not updated...

    def make_token_id(self, token):
        '''
            if token doesn't have an id yet, it is assigned one,
            and docs_per_token is set to 0 for that id
        '''
        if self.token_ids.get(token, -1) == -1:
            token_id = self.next_token_id

            self.token_ids[token] = token_id
            self.docs_per_token[token] = 0
            self.next_token_id += 1

    def add_and_count_doc(self, doc):
        '''add a doc for inference, but also analyze its token counts
            for the model.
        '''
        counts = self.add_doc_for_inference(doc)
        for token in counts.iterkeys():
            self.make_token_id(token)
            self.docs_per_token[token] += 1
        return counts

    def add_doc_for_inference(self, doc):
        '''takes a bug, stringifies it, and then produces a
            {token -> occurences} dict for the bug.

            also increments doc_count
        '''
        doc = self.bug_to_string(doc)
        tokens = self.tokenize(doc)

        self.doc_count += 1
        return self.count_tokens(tokens)

    def convert_and_filter_token_counts(self, token_counts):
        '''convert an iter of {token -> count} to {token_id -> count}
            while also filtering out tokens that are not part of the
            model.
        '''
        token_id_counts = {}
        for token in token_counts:
            if token in self.token_ids:
                token_id_counts[self.token_ids[token]] = token_counts[token]
        return token_id_counts

    def filter_tokens(self, low_threshold=2, high_threshold=0.95):
        '''filters tokens to only those which are significant
            i.e. they occur often but not always.
            if the thresholds are integers greater than 1 then they will 
            absolute document counts. If they are between 0 and 1 they will
            proportions
            default is 2 documents and high_threshold is 95%

            this should be called once all known bugs have been added'''
        new_token_ids = dict()

        self.next_token_id = 0
        low = low_threshold
        if (low < 1):
            low = math.ceil(low_threshold * self.doc_count)
        high = high_threshold
        if (high < 1):
            high = math.ceil(high_threshold * self.doc_count)

        self.token_ids = {}
        for token in self.docs_per_token.keys():
            occurences = self.docs_per_token[token]
            if low <= occurences and occurences <= high:
                self.token_ids[token] = self.next_token_id
                self.next_token_id += 1
            else:
                del self.docs_per_token[token]


    def filter_stopwords(self, tokens):
        ''' generates a filtered version of tokens, with all
            stopwords removed'''
        for token in tokens:
            if token in self.stopwords:
                continue
            if LDA.STOP_WORDS_PATTERN.match(token) is None:
                continue
            yield token
        
    @staticmethod
    def read_stop_words(stop_words_path):
        try:
            stopwords = set(open(stop_words_path).read().splitlines())
        except IOError:
            stopwords = set()
        stopwords.add("")
        stopwords.add("'s")
        return stopwords

    @staticmethod
    def count_tokens(tokens):
        """returns a map with the number of occurences of each token"""
        out = {}
        for i in tokens:
            out[i] = out.get(i,0) + 1
        return out

    def tokenize(self, text):
        return self.filter_stopwords(self.tokenizer.tokenize(text.lower()))

    @staticmethod
    def bug_to_string(bug):
        return bug

    @staticmethod
    def create_from_docs(docs):
        ''' return lda instance, dict of {id -> {token -> count}} '''
        lda = LDA()

        token_counts = [lda.add_and_count_doc(doc) for doc in docs]
        print 'filtering tokens'
        lda.filter_tokens()
        for i in range(len(token_counts)):
            counts = token_counts[i]
            token_counts[i] = lda.convert_and_filter_token_counts(counts)

        return lda, token_counts
        

class VowpalWabbit(object):
    def __init__(self, run, lda, alpha=0.1, beta=0.1, passes=2,
                    topic_count=100):
        self.lda = lda
        self.alpha = alpha
        self.beta = beta
        self.passes = passes
        self.topic_count = topic_count
        self.run = run

    def make_lda_input(self, docs, ids):
        '''docs = token -> count dicts, ids = ids of docs,
            in the same order'''
        with open(self.run.LDA_INPUT_FNAME, 'w+') as lda_input:
            # TODO: docs should be sorted by id
            for doc in docs:
                lda_input.write(self.doc_to_vw_lda(doc))

        with open(self.run.LDA_ID_INPUT_FNAME, 'w+') as lda_id_input:
            lda_id_input.write(json.dumps(map(str, ids), indent=2))

        with open(self.run.LDA_WORDS_INPUT_FNAME, 'w+') as lda_words_input:
            lda_words_input.write(json.dumps(self.lda.token_ids, indent=2))

    def token_bits(self):
        return int(math.ceil(math.log(len(self.lda.token_ids), 2)))

    def clean_files(self, files=None):
        files = files or [
            self.run.LDA_PREDICTIONS_FNAME,
            self.run.LDA_TOPICS_FNAME,       
            self.run.LDA_CACHE_FILE
        ]       
        for f in files:
            try:
                os.remove(f)
            except:
                pass

    def clean_files_for_inference(self):
        return self.clean_files([
            self.run.LDA_PREDICTIONS_FNAME,
            self.run.LDA_CACHE_FILE
        ])

    def lda_command(self):
        topic_count = str(self.topic_count)
        return "vw --lda %s --lda_alpha %s --lda_rho %s --minibatch 256 --power_t 0.5 --initial_t 1 -b %s --passes %s --cache_file %s -p %s --readable_model %s %s" % (
            topic_count,
            self.alpha,
            self.beta,
            self.token_bits(),
            self.passes,
            self.run.LDA_CACHE_FILE,
            self.run.LDA_PREDICTIONS_FNAME,
            self.run.LDA_TOPICS_FNAME,
            self.run.LDA_INPUT_FNAME
            )

    def lda_inference_command(self):
        topic_count = str(self.topic_count)
        # TODO: do we need -i to load the initial_regressor?
        return "vw --lda %s --testonly --lda_alpha %s --lda_rho %s --minibatch 256 --power_t 0.5 --initial_t 1 -b %s --passes %s --cache_file %s -p %s --readable_model %s %s" % (
            topic_count,
            self.alpha,
            self.beta,
            self.token_bits(),
            self.passes,
            self.run.LDA_CACHE_FILE,
            self.run.LDA_PREDICTIONS_FNAME,
            self.run.LDA_TOPICS_FNAME,
            self.run.LDA_INPUT_FNAME
            )


    def inform_loader(self, loader):
        print 'find document topic associations'
        # each line is the associations of a document to the topics
        self.read_vowpal_output(self.run.LDA_PREDICTIONS_FNAME,
                    lambda d, a: loader.set_document_topic_associations(a),
                    skip=self.lda.doc_count * (self.passes - 1))

    def create_summary(self):
        summary = LDASummary(self.lda, self.topic_count)
        summary.set_files([self.run.BUG_IDS_DUMP_FILE,
                self.run.TOKEN_DUMP_FILE,
                self.run.LDA_INPUT_FNAME,
                self.run.LDA_ID_INPUT_FNAME,
                self.run.LDA_WORDS_INPUT_FNAME,
                self.run.LDA_PREDICTIONS_FNAME,
                self.run.LDA_TOPICS_FNAME,
                self.run.LDA_CACHE_FILE])

        print 'find token topic associations'
        # each line is the associations of a token to the topics
        self.read_vowpal_output(self.run.LDA_TOPICS_FNAME,
                    summary.set_token_topic_associations)

        summary.calculate_topic_summaries()
        return summary

    @staticmethod
    def read_vowpal_output(fname, action, skip=0):
        '''
            read topic associations from a file, calling
            action(line_number, associations) for each line.

            vowpal metadata lines are skipped (eg. those at the start of
                the LDA_TOPICS_FNAME file) and not counted.

            in addition, you can skip a number of non-metadata lines
            (useful for ignoring previous passes in the predictors output)
        '''
        with open(fname) as lines:
            position = 0

            is_vowpal_metadata = lambda line: ':' in line or 'Version' in line
            lines = itertools.dropwhile(is_vowpal_metadata, iter(lines))
            lines = itertools.islice(lines, skip, None)
                # skip the first skip non-metadata lines

            for line in lines:
                line = line.rstrip().split()
                topic_associations = map(float, line)
                action(position, topic_associations)
                position += 1


    @staticmethod
    def doc_to_vw_lda(doc):
        doc = ' '.join([str(key) + ":" + str(doc[key]) for key in doc])
        return '| {}\n'.format(doc)


class LDASummary(object):
    def __init__(self, lda, topic_count):
        self.lda = lda
        self.topic_count = topic_count

        token_count = len(lda.token_ids)
        pow_2_token_count = 2 ** int(math.ceil(math.log(token_count, 2)))
            # round up to nearest power of 2 because VW will make up new
            # magical tokens for us that weren't in our docs

        print 'token count at summary create', token_count
        self.topic_token_matrix = [[0] * pow_2_token_count
                                    for i in range(topic_count)]
        self.topic_summaries = [None] * topic_count

    def set_token_topic_associations(self, token, associations):
        for topic in range(len(self.topic_token_matrix)):
            self.topic_token_matrix[topic][token] = associations[topic + 1]
                # skip associations[0] == float(token)



                
    def calculate_topic_summaries(self, max_words=25):
        tokens_by_id = reverse_dict(self.lda.token_ids)

        for topic in range(0, self.topic_count):
            token_associations = self.topic_token_matrix[topic]
            indices = sorted_indices(token_associations, reverse=True)
            words = [tokens_by_id.get(i,"") for i in indices[0:max_words]]

            self.topic_summaries[topic] = words

    def set_files(self, files):
        '''takes a list of files where each file name is of the form:
            some/path/components/<discard_this>-<keep_this>.<format>
            the file will be added to the report doc as <keep_this>.format
            any unrecognized file extensions will lead to the file being
            base64 encoded.
        '''
        self.files = [(f, '-'.join(os.path.basename(f).split('-')[1:])) \
                        for f in files]

    def make_report_doc(self, project):
        report = {
            'doc_id': uuid.uuid4().hex
            ,'project': project
            ,'generator': 'lda-run'
            ,'when': utc_now().isoformat()
            ,'topics': self.topic_count
        }
        return report
