
import logging
import os

from telemetry import configure, TestConfig, Resource, SERVICE_NAME
from telemetry import HttpConfig

from storecli.base import BaseStorageClient
from opentelemetry.instrumentation.celery import CeleryInstrumentor
from celery import Celery

if "SAMPLE_GRAFANA" in os.environ.keys():
    config = HttpConfig( "http://host.docker.internal:4318" )
    config.resource = Resource({ SERVICE_NAME: "service" })
    config.loglevel = logging.DEBUG
    configure(config)
else:
    config = TestConfig()
    config.resource = Resource({ SERVICE_NAME: "service" })
    config.loglevel = logging.DEBUG
    configure(config)

if "DEBUG_LOGS" in os.environ.keys():
    logging.getLogger().addHandler( logging.StreamHandler() )

MAX_NB_SANDBOX = 5

DEFAULT_TIME_LIMIT = 1.0
DEFAULT_WALL_TIME  = 1.0
DEFAULT_EXTRA_TIME = 0.1
DEFAULT_MEMORY_KB  = 256 * 1024 # 256 MB

SANDBOX_RESULT_FOLDER = "/app/results"

PYTHON_EXECUTABLE = "/usr/bin/python3"
CXX_COMPILER = "/usr/bin/g++"
JAVA_COMPILER = "/usr/bin/javac"
JAR_COMPILER = "/usr/bin/jar"
JAVA_EXECUTABLE = "/usr/bin/java"

STORAGE_CLIENT  = BaseStorageClient()
PROBLEM_STORAGE_LOCATION = "/problems"

CELERY_BACKEND = "redis://localhost:6379/0"
CELERY_BROKER  = "pyamqp://guest@localhost//"

MAX_LEN_ERROR_MESSAGE = 1024

judge_app = Celery(
    "judge",
    backend=CELERY_BACKEND,
    broker=CELERY_BROKER
)
CeleryInstrumentor().instrument()
