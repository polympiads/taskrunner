
import datetime
import re
from zoneinfo import ZoneInfo

import hypothesis.extra.django
from hypothesis import given, strategies as st

from ccs.utils.time import Reltime, Time
from ccs.utils.validators import validate_reltime, validate_reltime_nullable, validate_time, validate_time_nullable


class TestTimeUtils (hypothesis.extra.django.TestCase):
    @given(
        dt=st.datetimes(
            min_value=datetime.datetime(2026, 1, 1),
            max_value=datetime.datetime(2026, 12, 31)
        ),
        tz_name=st.sampled_from(["UTC", "Europe/Paris", "Asia/Tokyo", "America/New_York", "Australia/Adelaide"])
    )
    def test_consistency (self, dt: datetime.datetime, tz_name: str):
        REGEX = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}(Z|([+\-]\d{2}:\d{2}))"
        dt = datetime.datetime(
            dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second, 
            dt.microsecond - (dt.microsecond % 1000)
        )
        
        aware_dt = dt.replace(tzinfo=ZoneInfo(tz_name))
        
        target = Time.string_from_time(aware_dt)
        self.assertIsNotNone(re.match(REGEX, target))

        back, err = validate_time_nullable(None)
        self.assertIsNone(back)
        self.assertIsNone(err)
        back, err = validate_time_nullable(0)
        self.assertIsNone(back)
        self.assertEqual (err, "Field '{field}' should be a string")
        back, err = validate_time_nullable("fnjdsgf")
        self.assertIsNone(back)
        self.assertTrue  (err.startswith( "Field '{field}': ") )
        back, err = validate_time_nullable(target)
        self.assertIsNone(err)
        self.assertEqual(back.astimezone(datetime.timezone.utc), aware_dt.astimezone(datetime.timezone.utc))
        back, err = validate_time(None)
        self.assertIsNone(back)
        self.assertEqual (err, "Field '{field}' should exist")
        back, err = validate_time(0)
        self.assertIsNone(back)
        self.assertEqual (err, "Field '{field}' should be a string")
        back, err = validate_time("fnjdsgf")
        self.assertIsNone(back)
        self.assertTrue  (err.startswith( "Field '{field}': ") )
        back, err = validate_time(target)
        self.assertIsNone(err)
        self.assertEqual(back.astimezone(datetime.timezone.utc), aware_dt.astimezone(datetime.timezone.utc))

        back = Time.time_from_string(target)
        self.assertEqual(back.astimezone(datetime.timezone.utc), aware_dt.astimezone(datetime.timezone.utc))
    def test_invalid_time (self):
        with self.assertRaises(ValueError):
            time = Time.time_from_string( "0188514g5r" )

class TestReltimeUtils (hypothesis.extra.django.TestCase):
    @given(
        dt=st.timedeltas(
            min_value=- datetime.timedelta( 100 ),
            max_value=datetime.timedelta( 100 )
        )
    )
    def test_consistency (self, dt: datetime.timedelta):
        dt = datetime.timedelta( dt.days, dt.seconds, dt.microseconds - (dt.microseconds % 1000) )
        str = Reltime.string_from_reltime(dt)
        ndt = Reltime.reltime_from_string(str)

        back, err = validate_reltime_nullable(None)
        self.assertIsNone(back)
        self.assertIsNone(err)
        back, err = validate_reltime_nullable(0)
        self.assertIsNone(back)
        self.assertEqual (err, "Field '{field}' should be a string")
        back, err = validate_reltime_nullable("fnjdsgf")
        self.assertIsNone(back)
        self.assertTrue  (err.startswith( "Field '{field}': ") )
        back, err = validate_reltime_nullable(str)
        self.assertIsNone(err)
        self.assertEqual(back, ndt)
        back, err = validate_reltime(None)
        self.assertIsNone(back)
        self.assertEqual (err, "Field '{field}' should exist")
        back, err = validate_reltime(0)
        self.assertIsNone(back)
        self.assertEqual (err, "Field '{field}' should be a string")
        back, err = validate_reltime("fnjdsgf")
        self.assertIsNone(back)
        self.assertTrue  (err.startswith( "Field '{field}': ") )
        back, err = validate_reltime(str)
        self.assertIsNone(err)
        self.assertEqual(back, ndt)

        self.assertEqual(ndt, dt)
    def test_invalid_reltime (self):
        with self.assertRaises(ValueError):
            Reltime.reltime_from_string("45f4ed")
