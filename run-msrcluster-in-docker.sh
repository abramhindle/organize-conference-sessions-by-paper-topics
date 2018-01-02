# build the image
docker build -t vw ./docker/
docker run -v "`pwd`":/sessions-by-topic -t -i vw /bin/bash /run.sh $*
