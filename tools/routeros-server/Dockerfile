FROM ubuntu:24.04
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends iproute2 iptables ca-certificates procps && rm -rf /var/lib/apt/lists/*
WORKDIR /opt/wbd
COPY wbd-v4-server libwbd_engine.so ./
COPY entry.sh ./
COPY fixture/ ./fixture/
RUN chmod 755 wbd-v4-server entry.sh && chmod 600 fixture/key.pem fixture/route-key.hex fixture/users.json
ENV LD_LIBRARY_PATH=/opt/wbd
ARG WBD_CC=
ENV WBD_CC=$WBD_CC
STOPSIGNAL SIGTERM
ENTRYPOINT ["/opt/wbd/entry.sh"]
