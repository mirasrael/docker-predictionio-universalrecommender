FROM mirasrael/predictionio:0.12.0

RUN sudo apt-get update -y && sudo apt-get install maven -y

RUN git clone https://github.com/actionml/universal-recommender.git ~/ur; cd ~/ur; git checkout master
RUN git clone https://github.com/actionml/mahout.git ~/mahout; cd ~/mahout; git checkout sparse-speedup-13.0
RUN cd ~/mahout && sed -i 's/\/Users\/pat/\/home\/predictionio/g' /home/predictionio/mahout/build-scala-2.11.sh
RUN cd ~/mahout && ./build-scala-2.11.sh
RUN cd ~/ur \
  && sed -i -r 's/\/\/resolvers \+= .*/resolvers += "Local Repository" at "file:\/\/\/home\/predictionio\/.custom-scala-m2\/repo"/g' build.sbt \
  && sed -i 's/val mahoutVersion = "0.13.1-SNAPSHOT"/val mahoutVersion = "0.13.0"/' build.sbt \
  && sed -i 's/mahoutVersion classifier "spark_2.1"/mahoutVersion/' build.sbt
RUN cd ~/ur && pio build

WORKDIR /home/predictionio/ur

COPY ur-entrypoint.sh /ur-entrypoint.sh
RUN sudo chmod +x /ur-entrypoint.sh
COPY prepare-engine.sh /prepare-engine.sh
RUN sudo chmod +x /prepare-engine.sh

ONBUILD COPY engine.json /home/predictionio/ur/engine.json
ONBUILD RUN /prepare-engine.sh

ENTRYPOINT ["/ur-entrypoint.sh"]

CMD ["bash", "-c", "pio train -- --driver-memory 4G --executor-memory 4G && pio deploy"]


