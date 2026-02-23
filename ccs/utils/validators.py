
from ccs.utils.time import Reltime, Time

def validate_time_nullable (time: str):
    if time is None: return None, None
    if not isinstance(time, str): return None, "Field '{field}' should be a string"
    try:
        return Time.time_from_string(time), None
    except ValueError as err:
        return None, "Field '{field}': " + str(err)
def validate_reltime_nullable (time: str):
    if time is None: return None, None
    if not isinstance(time, str): return None, "Field '{field}' should be a string"
    try:
        return Reltime.reltime_from_string(time), None
    except ValueError as err:
        return None, "Field '{field}': " + str(err)

def validate_time (time: str):
    if time is None: return None, "Field '{field}' should exist"
    if not isinstance(time, str): return None, "Field '{field}' should be a string"
    try:
        return Time.time_from_string(time), None
    except ValueError as err:
        return None, "Field '{field}': " + str(err)
def validate_reltime (time: str):
    if time is None: return None, "Field '{field}' should exist"
    if not isinstance(time, str): return None, "Field '{field}' should be a string"
    try:
        return Reltime.reltime_from_string(time), None
    except ValueError as err:
        return None, "Field '{field}': " + str(err)
