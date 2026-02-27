
import asyncio
from datetime import timedelta
import json

from channels.layers import InMemoryChannelLayer, get_channel_layer, BaseChannelLayer
from django.test import TransactionTestCase

from ccs.models.contest import Contest
from ccs.models.eventfeed import EventFeed
from ccs.models.visible import Visibility
from ccs.tests.views.test_eventfeed import FakeEventFeedConsumer, override_layer
from django.contrib.auth.models import AnonymousUser
from freezegun import freeze_time

class TestContestStart (TransactionTestCase):
    def setUp(self):
        self._layer = override_layer()
        self._layer.enable()

        self.contest = asyncio.run( Contest.objects.acreate_contest(
            name         = "pubct",
            duration     = timedelta(hours=5),
            penalty_time = timedelta(minutes = 20),
            visibility   = Visibility.PUBLIC
        ) )
    def tearDown(self):
        self._layer.disable()
    def verify_consumer (self, *content, status = 200):
        _body = b"".join(self.consumer._bodies)
        _json = list(map(json.loads, _body.splitlines()))

        self.assertEqual(len(_json), len(content))
        for _js, _cn in zip(_json, content):
            self.assertEqual(_js, _cn)
        self.assertEqual(self.consumer._status, status)
    def test_empty_contest (self):
        self.consumer = FakeEventFeedConsumer(
            InMemoryChannelLayer(),
            AnonymousUser(),
            self.contest.pk
        )
        
        with self.assertRaises(asyncio.TimeoutError):
            asyncio.run( asyncio.wait_for( self.consumer.handle(b""), timeout=1 ) )

        base_uuid = EventFeed.objects.all()[0].pk
        self.verify_consumer(
            {"token": str(base_uuid), "id": "contest", "type": "contests",
               "data":{"id": str(self.contest.pk), "name": "pubct", "formal_name": "pubct",
                    "duration": "5:00:00.000",
                    "penalty_time": "0:20:00.000", "scoreboard_type": "pass-fail",
                    "scoreboard_freeze_duration": "0:00:00.000"}}
        )
    def test_start_contest (self):
        with freeze_time( "2025-04-14 13:30:00" ):
            Contest.objects.start_contest(self.contest.pk)
        
            with self.assertRaises(ValueError):
                Contest.objects.start_contest(self.contest.pk)

        self.consumer = FakeEventFeedConsumer(
            InMemoryChannelLayer(),
            AnonymousUser(),
            self.contest.pk
        )

        with self.assertRaises(asyncio.TimeoutError):
            asyncio.run( asyncio.wait_for( self.consumer.handle(b""), timeout=1 ) )

        base_uuid = EventFeed.objects.all()[0].pk
        self.verify_consumer(
            # Contest
            {"token": str(base_uuid), "id": "contest", "type": "contests",
               "data":{"name": "pubct", "formal_name": "pubct", "duration": "5:00:00.000",
                    "penalty_time": "0:20:00.000", "scoreboard_type": "pass-fail",
                    "scoreboard_freeze_duration": "0:00:00.000", "id": str(self.contest.pk)}},
            # Contest State
            {"token": str(base_uuid + 1), "id": "contest-start", "type": "state", "data": {
                "end_of_updates": None, "ended": None, "finalized": None, "frozen": None,
                "started": "2025-04-14T13:30:00.000Z", "thawed": None}},
            # Languages
            {"token": str(base_uuid + 2), "id": "python3", "type": "languages",
                "data": {"id": "python3", "name": "Python 3", "extensions": []}},
            {"token": str(base_uuid + 3), "id": "cpp", "type": "languages",
                "data": {"id": "cpp", "name": "GNU C++", "extensions": []}},
            {"token": str(base_uuid + 4), "id": "java", "type": "languages",
                "data": {"id": "java", "name": "Java", "extensions": []}},
            # Judgement Types
            {"token": str(base_uuid + 5), "id": "RE", "type": "judgement-types",
                "data": {"id": "RE", "name": "Runtime Error", "penalty": True, "solved": False}},
            {"token": str(base_uuid + 6), "id": "TLE", "type": "judgement-types",
                "data": {"id": "TLE", "name": "Time Limit Exceeded", "penalty": True, "solved": False}},
            {"token": str(base_uuid + 7), "id": "MLE", "type": "judgement-types",
                "data": {"id": "MLE", "name": "Memory Limit Exceeded", "penalty": True, "solved": False}},
            {"token": str(base_uuid + 8), "id": "WA", "type": "judgement-types",
                "data": {"id": "WA", "name": "Wrong Answer", "penalty": True, "solved": False}},
            {"token": str(base_uuid + 9), "id": "CE", "type": "judgement-types",
                "data": {"id": "CE", "name": "Compilation Error", "penalty": False, "solved": False}},
            {"token": str(base_uuid + 10), "id": "AC", "type": "judgement-types",
                "data": {"id": "AC", "name": "Accepted", "penalty": False, "solved": True}},
            {"token": str(base_uuid + 11), "id": "JE", "type": "judgement-types",
                "data": {"id": "JE", "name": "Judge Error", "penalty": False, "solved": False}}
        )
