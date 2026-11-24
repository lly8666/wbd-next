FROM python:3.11-bullseye
# Bullseye LTS ended 2026-08-31; ordinary mirrors now advertise removed files.
# Use the signed frozen package archives instead of floating old mirror indexes.
RUN printf '%s\n' \
    'deb [check-valid-until=no] https://archive.debian.org/debian bullseye main' \
    'deb [check-valid-until=no] https://archive.debian.org/debian bullseye-updates main' \
    'deb [check-valid-until=no] https://snapshot.debian.org/archive/debian-security/20260901T022952Z/ bullseye-security main' \
    > /etc/apt/sources.list && rm -f /etc/apt/sources.list.d/*.list /etc/apt/sources.list.d/*.sources && \
    apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    autoconf automake libtool make gcc g++ nasm binutils cmake pkg-config perl git curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN test "$(getconf GNU_LIBC_VERSION)" = "glibc 2.31" && \
    curl --proto '=https' -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain none --profile minimal
ENV PATH="/root/.cargo/bin:/opt/wbd-go/bin:${PATH}"
