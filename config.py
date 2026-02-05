
import logging

from telemetry import configure, TestConfig, Resource, SERVICE_NAME

config = TestConfig()
config.resource = Resource({ SERVICE_NAME: "service" })
config.loglevel = logging.DEBUG
configure(config)

MAX_NB_SANDBOX = 5
