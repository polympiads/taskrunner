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
RUN git reset --hard a918ac007fdfbfddc9a045d500cf72e3cd330e5b
RUN make
RUN make install

# Install Java
RUN apt-get update
RUN apt-get install -y openjdk-21-jdk

# Install tools
RUN apt-get update
RUN apt-get install -y nano

# Setup task runner
RUN apt-get update
RUN apt-get install -y python3 python3-pip

RUN apt-get update
RUN apt-get install texlive-latex-extra texlive-fonts-recommended

WORKDIR /app
COPY requirements.txt .

RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt
COPY . .

RUN python3 manage.py makemigrations

ENV TEST_JUDGE=yes
#ENV DEBUG_LOGS=yes
#ENV SAMPLE_GRAFANA=yes

CMD ["bash", "runner.sh"]