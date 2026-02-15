
import logging

from telemetry     import traces
from opentelemetry import trace

sandbox_logger = logging.getLogger("storecli")
sandbox_tracer = traces.get_tracer("storecli")

start_as_current_span = sandbox_tracer.start_as_current_span
