FROM python:3.11-bullseye
RUN apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    autoconf automake libtool make gcc g++ nasm binutils cmake pkg-config perl git curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN test "$(getconf GNU_LIBC_VERSION)" = "glibc 2.31" && \
    curl --proto '=https' -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain none --profile minimal
ENV PATH="/root/.cargo/bin:/opt/wbd-go/bin:${PATH}"
