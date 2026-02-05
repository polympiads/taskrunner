
import logging

from telemetry import configure, TestConfig, Resource, SERVICE_NAME

config = TestConfig()
config.resource = Resource({ SERVICE_NAME: "service" })
config.loglevel = logging.DEBUG
configure(config)

MAX_NB_SANDBOX = 5

DEFAULT_TIME_LIMIT = 1.0
DEFAULT_WALL_TIME  = 1.0
DEFAULT_EXTRA_TIME = 0.1
DEFAULT_MEMORY_KB  = 256 * 1024 # 256 MB

SANDBOX_RESULT_FOLDER = "/app/results"
