FROM ubuntu:24.04
RUN apt-get update && apt-get install -y --no-install-recommends iproute2 && rm -rf /var/lib/apt/lists/*
WORKDIR /opt/lab
COPY kernel-probe entry.sh ./
COPY bin/ ./bin/
RUN chmod 755 kernel-probe entry.sh
ARG BBR_LAB_CC=kernel
ENV BBR_LAB_CC=$BBR_LAB_CC
ENTRYPOINT ["/opt/lab/entry.sh"]
