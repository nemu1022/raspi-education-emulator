FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    gdb \
    git \
    make \
    python3 \
    python3-pip \
    qemu-system-arm \
    qemu-system-aarch64 \
    gcc-arm-none-eabi \
    binutils-arm-none-eabi \
    gdb-multiarch \
    && apt-get clean

WORKDIR /workspace