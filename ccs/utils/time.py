
import datetime
import math
import re

class Time:
    @staticmethod
    def string_from_time (time: datetime.datetime) -> str:
        result = time.isoformat(timespec="milliseconds")

        return result.replace("+00:00", "Z")
    @staticmethod
    def time_from_string (time: str) -> datetime.datetime:
        try:
            if time.endswith("Z"):
                time = time[:-1] + "+00:00"

            return datetime.datetime.fromisoformat(time)
        except Exception:
            raise ValueError( f"Invalid time format: {time}" )

class Reltime:
    @staticmethod
    def string_from_reltime (time: datetime.timedelta) -> str:
        total_seconds = time.total_seconds()
        is_negative = total_seconds < 0
        abs_seconds = abs(total_seconds)

        abs_full_milliseconds = math.floor(abs_seconds * 1000 + 1e-4)
        abs_full_seconds      = abs_full_milliseconds // 1000
        milliseconds          = abs_full_milliseconds % 1000

        hours   =  abs_full_seconds // 3600
        minutes = (abs_full_seconds %  3600) // 60
        seconds =  abs_full_seconds %  60

        time_str = f"{hours}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"

        return f"-{time_str}" if is_negative else time_str
    @staticmethod
    def reltime_from_string (time: str) -> datetime.timedelta:
        reltime_regex = r"(-)?(\d+)\:(\d{2})\:(\d{2})(?:\.(\d{3}))?"
        
        match = re.fullmatch(reltime_regex, time)
        if not match:
            raise ValueError( f"Invalid relative time format: {time}" )
        
        is_negative = match.group(1) == '-'
        
        hours   = int(match.group(2))
        minutes = int(match.group(3))
        seconds = int(match.group(4))
        millis  = int(match.group(5) or 0)

        delta = datetime.timedelta( hours = hours, minutes = minutes, seconds = seconds, milliseconds=millis )

        return - delta if is_negative else delta
