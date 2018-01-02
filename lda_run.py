import os

class LDARun():
    def __init__(self):
        workdir =  'out'
        #print workdir
        os.system('mkdir -p {}'.format(workdir))

        def wd(path):
            project = "lda"
            return 'out/' + path.format(project)
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
