#!/bin/bash
cd /sessions-by-topic
python msrcluster.py $* | tee msrcluster.output
