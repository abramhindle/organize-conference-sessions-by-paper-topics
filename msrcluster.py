import lda
from os import listdir
from os.path import isfile, join
import json
import lda_run
import os
import datetime, itertools, json, os, shlex, shutil, string
import subprocess
from dateutil.tz import tzutc
import numpy
import sklearn.cluster
import argparse

parser = argparse.ArgumentParser(description='Cluster Texts Into Sessions')
parser.add_argument('-T', default=20, help='Number of Topics')
parser.add_argument('-S', default=8, help='Number of sesssions')
args = parser.parse_args()
topic_count = int(args.T)
n_clusters = int(args.S)


# pycruft http://stackoverflow.com/users/346573/pycruft from http://stackoverflow.com/a/3207973
mypath = "./texts/"
corpus_files = [mypath + f for f in listdir(mypath) if isfile(join(mypath, f))]
texts = [file(f).read() for f in corpus_files]
my_lda = lda.LDA.create_from_docs(texts)
run = lda_run.LDARun()
vw = lda.VowpalWabbit(run, my_lda[0], passes=10, topic_count=topic_count)
vw.make_lda_input(my_lda[1], corpus_files)
vw.clean_files()

def run_command(command):
    '''safely run a command as a subprocess and print out any output or error
        messages it produces.'''
    if type(command) is str:
        command = shlex.split(command)
    try:
        subprocess.check_output(command)
    except subprocess.CalledProcessError as e:
        print 'failed with return code {}'.format(e.returncode)
        print e.output
        print 'returned {}'.format(e.returncode)
        sys.stdout.flush()
        raise

run_command(vw.lda_command())
summary = vw.create_summary()
report = summary.make_report_doc("")

x = numpy.zeros((len(texts),topic_count))
def loader(d,a):
    x[d,0:topic_count] = a[0:topic_count]


vw.read_vowpal_output(run.LDA_PREDICTIONS_FNAME,
                      loader,
                      skip=vw.lda.doc_count * (vw.passes - 1))

xn = x / numpy.sum(x,axis=1).reshape((len(texts),1))
kmeans = sklearn.cluster.KMeans(n_clusters=n_clusters).fit(xn)
# print  numpy.bincount(kmeans.labels_)
# now lets look at accepted papers
l = [mypath + x.strip() for x in file("accepted.txt").readlines()]
indices = [i for i in range(0,len(corpus_files)) if corpus_files[i] in l]
subxn = xn[indices]
kmeans = sklearn.cluster.KMeans(n_clusters=n_clusters).fit(subxn)
# print  numpy.bincount(kmeans.labels_)
# todo: load CSV file to get metadata
import csv
csvfilename = "metadata.csv"
metadata = dict()
with open(csvfilename, 'rb') as csvfile:
    reader = csv.reader(csvfile, delimiter=',', quotechar='"')
    for row in reader:
        number = row[0]
        filename = "%s%s.txt" % ( mypath , number )
        metadata[filename] = row

#
import sys
writer = csv.writer(sys.stdout, delimiter=',',quotechar='"', quoting=csv.QUOTE_MINIMAL)

for i in range(0,n_clusters):
    print "############################"
    print "Cluster %s:" % i
    for j in range(0,len(indices)):
        if kmeans.labels_[j] == i:
            writer.writerow([str(i)] + metadata[corpus_files[indices[j]]])

