FROM thingsboard/tb-gateway:3.8.6

USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends unixodbc odbc-postgresql \
    && rm -rf /var/lib/apt/lists/*
