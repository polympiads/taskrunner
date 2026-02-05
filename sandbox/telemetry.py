
import logging

from telemetry     import traces
from opentelemetry import trace

sandbox_logger = logging.getLogger("sandbox")
sandbox_tracer = traces.get_tracer("sandbox")

start_as_current_span = sandbox_tracer.start_as_current_span
