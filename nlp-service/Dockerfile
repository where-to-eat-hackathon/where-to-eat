FROM docker.io/mambaorg/micromamba:1.5.1-alpine
WORKDIR /nlp-service

USER root
RUN adduser -DH worker && chown -R worker /nlp-service
USER worker

ADD ./env.yaml /nlp-service/env.yaml
RUN micromamba create -n nlp-service -f env.yaml -c pytorch -y
ADD . /nlp-service/

CMD ["micromamba", "run", "-n", "nlp-service", "python", "main.py"]
