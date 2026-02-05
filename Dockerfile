FROM ubuntu:24.04

# Install isolate
WORKDIR /tools/isolate

RUN apt-get update
RUN apt-get install -y libcap-dev asciidoc-base
RUN apt-get install -y git
RUN apt-get install -y build-essential
RUN apt-get install -y pkg-config
RUN apt-get install -y libsystemd-dev

RUN git clone https://github.com/ioi/isolate.git isolate-github

WORKDIR /tools/isolate/isolate-github
RUN make
RUN make install

# Setup task runner
RUN apt-get update
RUN apt-get install -y python3 python3-pip

WORKDIR /app
COPY . .

RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

CMD ["tail", "-f", "/dev/null"]