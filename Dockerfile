FROM ubuntu:noble-20251013
WORKDIR /usr/local/lib

RUN apt update && apt install -y build-essential clang bison flex libreadline-dev gawk tcl-dev libffi-dev libftdi-dev mercurial graphviz xdot \
pkg-config python3 python3-pip libboost-all-dev cmake make yosys arachne-pnr python3 python3-venv python3-pip git make && rm -rf /var/cache/apt/archives /var/lib/apt/lists/*

# Copy local iCEFARM source and install from it
COPY iCEFARM/ /usr/local/lib/iCEFARM/

WORKDIR /usr/local/app
COPY BitstreamEvolutionPico2ice/ /usr/local/app/

RUN python3 -m venv .venv
RUN .venv/bin/pip install pyserial numpy matplotlib sortedcontainers pytest ascutil
RUN .venv/bin/pip install /usr/local/lib/iCEFARM/
RUN make init
COPY BitstreamEvolutionPico2ice/data/seed-hardware.asc data/seed-hardware.asc
