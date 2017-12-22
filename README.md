# organize-conference-sessions-by-paper-topics

Do you have a lot of papers submitted to your conference and now you have to organize the conference into sessions and you're not sure how?

Why not apply topic analysis so you can group similar papers together into clusters?

This program uses LDA to characterize the topics of ALL SUBMITTED papers. Then applies k-means to organize the accepted papers into meaningful sessions!

# Requirements

* Vowpal Wabbit  http://hunch.net/~vw/ - apt-get install vw 
* python2
* numpy - pip install --user numpy
* nltk - pip install --user nltk
* pdftotext -- get poppler-utils - apt-get install poppler-utils # https://linuxappfinder.com/package/poppler-utils

# How to run it?

You need TXT files of all the papers in the texts/ directory
You can make these files by putting all submitted paper PDF into that directory and running

```
cd texts
for file in *.pdf
do
    pdftotext $file
done

```

Then in accepted.txt list just the filenames (not the path) of all accepted papers.

Then in metadata.csv fill in the details of the ACCEPTED IDs and the author names and titles of the paper (you can get this from easychair.

Then run msrcluster.py, but Vowpal wabbit (vw) needs to be the path.
```
python msrcluster.py
```

You may also set the number of sessions and topics:

```
usage: msrcluster.py [-h] [-T T] [-S S]

Cluster Texts Into Sessions

optional arguments:
  -h, --help  show this help message and exit
  -T T        Number of Topics
  -S S        Number of sesssions
```

It outputs text of example sessions. For example the sample data I provide should do something like this:

```
hindle1@frail:~/projects/sessions-by-topic$ python msrcluster.py -T 17 -S 10
filtering tokens
out
predictions = out/lda-predictions.dat
Num weight bits = 14
learning rate = 0.5
initial_t = 1
power_t = 0.5
decay_learning_rate = 1
creating cache_file = out/lda-topics.dat.cache
Reading datafile = out/lda-vr_lda_input.lda.txt
num sources = 1
average  since         example        example  current  current  current
loss     last          counter         weight    label  predict features
9.684358 9.684358            1            1.0  unknown   0.0000      997
9.717879 9.751401            2            2.0  unknown   0.0000     1393
9.719991 9.722104            4            4.0  unknown   0.0000      543
9.729306 9.738621            8            8.0  unknown   0.0000      706
10.343038 10.956770           16           16.0  unknown   0.0000     1166
10.644665 10.946292           32           32.0  unknown   0.0000     1391
10.800557 10.956450           64           64.0  unknown   0.0000      701
9.801880 8.803202          128          128.0  unknown   0.0000     1335
8.998146 8.194412          256          256.0  unknown   0.0000      557
8.466152 7.934158          512          512.0  unknown   0.0000      706

finished run
number of examples = 720
weighted example sum = 720.000000
weighted label sum = 0.000000
average loss = 0.000000 h
total feature number = 742680
token count at summary create 9647
find token topic associations
############################
Cluster 0:
0,bazelli2013ICSMERA-Personality,Personality,bazelli
0,chowdhury2015MSR-IRC,IRC,chowdhury
0,hindle2005MSR-SCQL,SCQL,hindle
############################
Cluster 1:
1,hindle2017NIME-Dijj,Dijj,hindle
1,hindleMSR2008-large-changes,large-changes,hindleMSR
1,hindleICPC2009-large-changes-classification,large-changes-classification,hindleICPC
1,posnett2011WCRE-Got-Issues,Got-Issues,posnett
1,hindle2008SCAM-indentation-shape,indentation-shape,hindle
############################
Cluster 2:
2,hindle2016EMSE-bugdedup,bugdedup,hindle
2,posnett2011MSR-readability,readability,posnett
2,hindle2008ICPC-reading-beside-the-lines,reading-beside-the-lines,hindle
2,alipour2013MSR-bugdedup,bugdedup,alipour
############################
Cluster 3:
3,chowdhury2015IGSC-systemcall,systemcall,chowdhury
3,romansky2017ICSME-timeseries,timeseries,romansky
3,chowdhuryMSR2016-eProjects,eProjects,chowdhury
3,hasan2016ICSE-Energy-Profiles-of-Java-Collections-Classes,Energy-Profiles-of-Java-Collections-Classes,hasan
3,hu2012MSR-builddeps,builddeps,hu
3,pang2016ICSMEERA,pang2016ICSMEERA,pang
3,zhang2014IEEESoftware-user-choice,user-choice,zhang
############################
Cluster 4:
4,davies2011MSR-bertillonage,bertillonage,davies
4,barr2012cid,barr2012cid,barr
4,hindle2016CACM,hindle2016CACM,hindle
4,davies2012ESME-Bertillonage,Bertillonage,davies
############################
Cluster 5:
5,burlet2015MSR-music-coders,music-coders,burlet
5,hindle2014NIME-cloudorch,cloudorch,hindle
5,hindle2011ICSENIER-Multifractal,Multifractal,hindle
5,hindle2016NIME-hacking-nimes,hacking-nimes,hindle
5,hindle2013NIME-SWARMED,SWARMED,hindle
############################
Cluster 6:
6,hindle2007MSR-Release-Pattern-Discovery,Release-Pattern-Discovery,hindle
6,hindle2007ICSM-release-pattern,release-pattern,hindle
6,campbell2013MSR-Deficient,Deficient,campbell
############################
Cluster 7:
7,hindle2012MSR-Green-Mining,Green-Mining,hindle
7,hindle2012ICSENEIR-Green-Mining,Green-Mining,hindle
############################
Cluster 8:
8,romansky2014CASCON,romansky2014CASCON,romansky
8,aggarwal2015ICSME-greenadvisor,greenadvisor,aggarwal
8,german2004SEKE-softChange,softChange,german
8,hindle2011EMSE-automated-topic-naming,automated-topic-naming,hindle
8,burlet2017PeerJ,burlet2017PeerJ,burlet
############################
Cluster 9:
9,rasmussen2014GREENS-adblock,adblock,rasmussen
9,hindle2010MSR-Challenge-Description,Challenge-Description,hindle
```
