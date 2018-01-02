# This is to give you a docker where you can run this program 
# It is not meant to run the program for you but will give you
# a working environment

FROM ubuntu:17.10

MAINTAINER Abram Hindle hindle1@ualberta.ca

RUN apt-get update && apt-get install -y \
    build-essential \
    python \
    python-dev \
    python-pip \
    git \
    uuid-dev \
    sqlite3 \
    libsqlite3-dev \
    libtool \
    automake \
    poppler-utils \
    libboost-all-dev \
    cmake || echo "Ignoring poor return value"

#install perl and python
RUN apt-get install -y \
    wget \
    python-numpy \
    python-scipy

# Fix R LOCALE errors
ENV LANG "en_US.UTF-8"

# locales
RUN apt-get install -y locales
RUN locale-gen en_US.UTF-8
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en
ENV LC_ALL en_US.UTF-8

# python deps
RUN pip install nltk 

RUN apt-get -y install zlib1g-dev

# setup vowpal_wabbit - checkout version 8.5.0
RUN cd && git clone https://github.com/JohnLangford/vowpal_wabbit.git && \
    cd vowpal_wabbit && \
    git checkout tags/8.5.0 && \
    autoreconf -vfi && \
    ./configure --with-boost-libdir=/usr/lib/x86_64-linux-gnu && \
    make -j 8 && make install

RUN apt-get -y install apt-utils
RUN apt-get -y install pkg-config
RUN apt-get -y install python-dateutil python-sklearn
ADD ./run.sh /

ENV LOGNAME docker
