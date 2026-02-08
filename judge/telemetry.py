import logging

from telemetry     import traces
from opentelemetry import trace

judge_logger = logging.getLogger("judge")
judge_tracer = traces.get_tracer("judge")

start_as_current_span = judge_tracer.start_as_current_span
