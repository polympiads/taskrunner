import logging

from telemetry     import traces
from opentelemetry import trace

problems_logger = logging.getLogger("problems")
problems_tracer = traces.get_tracer("problems")

start_as_current_span = problems_tracer.start_as_current_span
