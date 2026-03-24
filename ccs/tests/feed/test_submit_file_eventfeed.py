
import datetime
import json
import os
from unittest.mock import patch
from django.conf import settings
from django.test import TransactionTestCase, override_settings
from freezegun import freeze_time

from balloons.models import Balloon
from ccs.models.contest import Contest, ContestRole
from ccs.models.eventfeed import EventFeed
from ccs.models.managers.contest import ContestManager
from ccs.models.visible import Visibility
from ccs.tests.views.test_eventfeed import override_layer
from ccs.utils.time import Reltime, Time
from judge.languages import LanguageKind
from judge.tests.languages.test_cpp import APLUSB_PROG as APLUSB_PROG_CPP
from judge.tests.languages.test_java import APLUSB_PROG as APLUSB_PROG_JAVA
from judge.tests.languages.test_python import APLUSB_PROG as APLUSB_PROG_PYTHON
from judge.tests.tasks.icpc.test_scheduler import eager_celery
from problems.models.problem import Problem
from django.core.management import call_command
from django.contrib.auth.models import User

from problems.tests.management.test_prepare_polygon_cmd import APLUSB_FILE
from problems.tests.tasks.polygon.test_prepare import get_test_package_location
from storecli.inmemory import InMemoryStorageClient
from submit.models.submission import Submission, SubmitError
from submit.models.verdict import SubmissionVerdict
from django.conf import settings

from taskrunner.celery import judge_app
from asgiref.sync import async_to_sync, sync_to_async

APLUSB_PROG_CPP_SMALL_TLE = """
#include <iostream>

int main () {
    int a, b;
    std::cin >> a >> b;
    volatile int u = 0;
    volatile int v = 0;
    for (int i = 0; i < 10 * 1000 * 1000; i ++) {
        u ++;
        v --;
    }
    std::cout << a + b + u + v << "\\n";
}
"""
APLUSB_PROG_CPP_SMALL_MLE = """
#include <iostream>

const int MAXN = 1024 * 1024;
int dp[MAXN];
int main () {
    int a, b;
    std::cin >> a >> b;
    for (int u = 0; u < MAXN; u += 2) {
        dp[u] = 1;
        dp[u + 1] = -1;
    }
    for (int u = 0; u < MAXN; u ++) a += dp[u];
    std::cout << a + b << "\\n";
}
"""

class TestSubmitFileManager (TransactionTestCase):
    def setUp(self):
        self.inmemory_storage = InMemoryStorageClient(settings.STORAGE_CLIENT_LOCATION)
        self.patch_storage = override_settings(STORAGE_CLIENT=self.inmemory_storage)
        self.patch_storage.__enter__()

        self.contest1 = async_to_sync(ContestManager.acreate_contest)(
            name         = "hc2",
            duration     = datetime.timedelta(hours = 5),
            penalty_time = datetime.timedelta(minutes = 20),
            visibility   = Visibility.PUBLIC,

            scoreboard_freeze_duration = None
        )
        ContestManager.start_contest(self.contest1.pk)
        self.contest1.refresh_from_db()
        self.contest2 = async_to_sync(ContestManager.acreate_contest)(
            name         = "hc2",
            duration     = datetime.timedelta(hours = 5),
            penalty_time = datetime.timedelta(minutes = 20),
            visibility   = Visibility.PUBLIC
        )

        with freeze_time("2025-04-14 13:30:00"):
            self.contest3 = async_to_sync(ContestManager.acreate_contest)(
                name         = "hc2",
                duration     = datetime.timedelta(hours = 5),
                penalty_time = datetime.timedelta(minutes = 20),
                visibility   = Visibility.PUBLIC,
                scoreboard_freeze_duration = datetime.timedelta(hours = 1)
            )
            ContestManager.start_contest(self.contest3.pk)
            self.contest3.refresh_from_db()
        
        self.inc_user   = User.objects.create_user("inc_user")
        self.team_user  = User.objects.create_user("team_user")
        self.judge_user = User.objects.create_user("judge_user")
        ContestManager.add_accounts(self.contest1.pk, [(self.team_user, ContestRole.TEAM), (self.judge_user, ContestRole.JUDGE)])
        ContestManager.add_accounts(self.contest2.pk, [(self.team_user, ContestRole.TEAM), (self.judge_user, ContestRole.JUDGE)])
        ContestManager.add_accounts(self.contest3.pk, [(self.team_user, ContestRole.TEAM), (self.judge_user, ContestRole.JUDGE)])
        EventFeed.objects.all().delete()
    def tearDown(self):
        self.patch_storage.__exit__(None, None, None)

    def mkfile (self, file: str):
        return os.path.abspath(os.path.join(os.path.dirname(__file__), file))

    @override_layer()
    @freeze_time("2025-04-14 13:29:59.999")
    def test_submit_file_before_start (self):
        problem = Problem.objects.create()

        with eager_celery():
            call_command("prepare_polygon", problem.pk, APLUSB_FILE)
            problem = Problem.objects.get(pk = problem.pk)
            with open(self.mkfile("index.cpp"), "w") as file:
                file.write(APLUSB_PROG_CPP)
            with self.assertRaisesRegex(SubmitError, "Cannot create submission for contest that hasn't started\\."):
                call_command("submit_file", self.team_user.pk, problem.pk, self.mkfile("index.cpp"), contest = self.contest2.pk)
            with self.assertRaisesRegex(SubmitError, "User cannot create a submission in that contest\\."):
                call_command("submit_file", self.inc_user.pk, problem.pk, self.mkfile("index.cpp"), contest = self.contest2.pk)

    @override_layer()
    @freeze_time("2025-04-14 18:30:00.001")
    def test_submit_file_after_end (self):
        problem = Problem.objects.create()

        with eager_celery():
            call_command("prepare_polygon", problem.pk, APLUSB_FILE)
            problem = Problem.objects.get(pk = problem.pk)
            with open(self.mkfile("index.cpp"), "w") as file:
                file.write(APLUSB_PROG_CPP)
            with self.assertRaisesRegex(SubmitError, "Cannot create submission after the end of the contest\\."):
                call_command("submit_file", self.team_user.pk, problem.pk, self.mkfile("index.cpp"), contest = self.contest3.pk)
            with self.assertRaisesRegex(SubmitError, "User cannot create a submission in that contest\\."):
                call_command("submit_file", self.inc_user.pk, problem.pk, self.mkfile("index.cpp"), contest = self.contest3.pk)

    @override_layer()
    def test_judge_can_submit_anytime (self):
        problem = Problem.objects.create()
        with eager_celery():
            call_command("prepare_polygon", problem.pk, APLUSB_FILE)
            problem = Problem.objects.get(pk = problem.pk)

        for time in ["2025-04-14 13:30:00.000", "2025-04-14 14:31:47.521", "2025-04-14 18:30:00.000", "2025-04-21 18:30:00.000"]:
            with freeze_time(time):
                EventFeed.objects.all().delete()

                with eager_celery():
                    with open(self.mkfile("index.cpp"), "w") as file:
                        file.write(APLUSB_PROG_CPP)
                    call_command("submit_file", self.judge_user.pk, problem.pk, self.mkfile("index.cpp"), contest = self.contest3.pk)
                
                submission = list(Submission.objects.all())[-1]

                payloads = list(map(lambda evt: json.loads(evt.full_payload), EventFeed.objects.all()))
                prvts = list(map(lambda evt: (evt.visibility, evt.owner), EventFeed.objects.all()))
                evt1 = EventFeed.objects.all()[0].pk

                for x in prvts:
                    self.assertEqual(x, (Visibility.PRIVATE, self.judge_user))

                subid = str(submission.pk)
                pid = str(problem.pk)
                self.assertEqual(len(payloads), 6)
                self.assertEqual(payloads[0],
                    { "token": str(evt1), "id": subid, "type": "submission",
                    "data": {"id": subid, "language_id": "cpp", "problem_id": pid, "account_id": str(self.judge_user.pk),
                        "time": Time.string_from_time(datetime.datetime.fromisoformat(time + "Z")),
                        "contest_time": Reltime.string_from_reltime(
                            max(
                                datetime.timedelta(),
                                datetime.datetime.fromisoformat(time + "Z") - self.contest3.started
                            ) if self.contest3.started is not None else datetime.timedelta() 
                        )} })
                self.assertEqual(payloads[1],
                    { "token": str(evt1 + 1), "id": subid, "type": "submission-state",
                    "data": {"submission_id": subid, "status": "starting"} })
                self.assertEqual(payloads[2],
                    { "token": str(evt1 + 2), "id": subid, "type": "submission-state",
                    "data": {"submission_id": subid, "status": "compiling"} })
                self.assertEqual(payloads[3],
                    { "token": str(evt1 + 3), "id": subid, "type": "submission-state",
                    "data": {"submission_id": subid, "status": "running"} })
                self.assertEqual(payloads[4],
                    { "token": str(evt1 + 4), "id": subid, "type": "submission-state",
                    "data": {"submission_id": subid, "status": "finished"} })
                self.assertEqual(payloads[5],
                    { "token": str(evt1 + 5), "id": subid, "type": "judgements",
                    "data": {"id": subid, "submission_id": subid, "judgement_type_id": "AC"} })
    @override_layer()
    def test_judge_can_submit_before_contest (self):
        problem = Problem.objects.create()
        with eager_celery():
            call_command("prepare_polygon", problem.pk, APLUSB_FILE)
            problem = Problem.objects.get(pk = problem.pk)

    @override_layer()
    def test_submit_during_contest (self):
        problem = Problem.objects.create()
        with eager_celery():
            call_command("prepare_polygon", problem.pk, APLUSB_FILE)
            problem = Problem.objects.get(pk = problem.pk)

        offset = -1
        for time in ["2025-04-14 13:30:00.000", "2025-04-14 14:31:47.521", "2025-04-14 17:29:59", "2025-04-14 17:30:00", "2025-04-14 18:30:00.000"]:
            offset += 1
            with freeze_time(time):
                EventFeed.objects.all().delete()

                with eager_celery():
                    with open(self.mkfile("index.cpp"), "w") as file:
                        file.write(APLUSB_PROG_CPP)
                    call_command("submit_file", self.team_user.pk, problem.pk, self.mkfile("index.cpp"), contest = self.contest3.pk)
                    with self.assertRaisesRegex(SubmitError, "User cannot create a submission in that contest\\."):
                        call_command("submit_file", self.inc_user.pk, problem.pk, self.mkfile("index.cpp"), contest = self.contest3.pk)
                
                submission = list(Submission.objects.all())[-1]

                payloads = list(map(lambda evt: json.loads(evt.full_payload), EventFeed.objects.all()))
                prvts = list(map(lambda evt: (evt.visibility, evt.owner), EventFeed.objects.all()))
                evt1 = EventFeed.objects.all()[0].pk

                if offset < 3:
                    self.assertEqual(prvts[-1], (Visibility.PRIVATE, None))
                    for x in prvts[1:-2]:
                        self.assertEqual(x, (Visibility.PRIVATE, self.team_user))
                    for x in [prvts[0], prvts[-2]]:
                        self.assertEqual(x, (Visibility.PUBLIC, self.team_user))
                else:
                    for x in prvts[1:]:
                        self.assertEqual(x, (Visibility.PRIVATE, self.team_user))
                    for x in [prvts[0]]:
                        self.assertEqual(x, (Visibility.PUBLIC, self.team_user))

                subid = str(submission.pk)
                pid = str(problem.pk)
                
                if offset < 3:
                    self.assertEqual(len(payloads), 7)
                    balloon = Balloon.objects.get()
                else:
                    self.assertEqual(len(payloads), 6)
                self.assertEqual(payloads[0],
                    { "token": str(evt1), "id": subid, "type": "submission",
                    "data": {"id": subid, "language_id": "cpp", "problem_id": pid, "account_id": str(self.team_user.pk),
                        "time": Time.string_from_time(datetime.datetime.fromisoformat(time + "Z")),
                        "contest_time": Reltime.string_from_reltime(
                            max(
                                datetime.timedelta(),
                                datetime.datetime.fromisoformat(time + "Z") - self.contest3.started
                            ) if self.contest3.started is not None else datetime.timedelta() 
                        )} })
                self.assertEqual(payloads[1],
                    { "token": str(evt1 + 1), "id": subid, "type": "submission-state",
                    "data": {"submission_id": subid, "status": "starting"} })
                self.assertEqual(payloads[2],
                    { "token": str(evt1 + 2), "id": subid, "type": "submission-state",
                    "data": {"submission_id": subid, "status": "compiling"} })
                self.assertEqual(payloads[3],
                    { "token": str(evt1 + 3), "id": subid, "type": "submission-state",
                    "data": {"submission_id": subid, "status": "running"} })
                self.assertEqual(payloads[4],
                    { "token": str(evt1 + 4), "id": subid, "type": "submission-state",
                    "data": {"submission_id": subid, "status": "finished"} })
                self.assertEqual(payloads[5],
                    { "token": str(evt1 + 5), "id": subid, "type": "judgements",
                    "data": {"id": subid, "submission_id": subid, "judgement_type_id": "AC"} })
                if offset < 3:
                    self.assertEqual(payloads[6],
                        { "token": str(evt1 + 6), "id": str(balloon.pk), "type": "balloons",
                        "data": {"id": str(balloon.pk), "problem_id": str(problem.id), "account_id": str(self.team_user.pk), "status": "pending"} })
                    balloon.delete()

    @override_layer()
    def test_submit_file_cpp_aplusb (self):
        problem = Problem.objects.create()

        with eager_celery():
            call_command("prepare_polygon", problem.pk, APLUSB_FILE)
            problem = Problem.objects.get(pk = problem.pk)
            with open(self.mkfile("index.cpp"), "w") as file:
                file.write(APLUSB_PROG_CPP)
            call_command("submit_file", self.team_user.pk, problem.pk, self.mkfile("index.cpp"), contest = self.contest1.pk)
        
        submission = Submission.objects.all()[0]

        payloads = list(map(lambda evt: json.loads(evt.full_payload), EventFeed.objects.all()))
        evt1 = EventFeed.objects.all()[0].pk

        balloon = Balloon.objects.get()

        subid = str(submission.pk)
        pid = str(problem.pk)
        self.assertEqual(len(payloads), 7)
        self.assertEqual(payloads[0],
            { "token": str(evt1), "id": subid, "type": "submission",
             "data": {"id": subid, "language_id": "cpp", "problem_id": pid, "account_id": str(self.team_user.pk),
                "time": Time.string_from_time(submission.created_at),
                "contest_time": Reltime.string_from_reltime(
                    max(
                        datetime.timedelta(),
                        submission.created_at - self.contest1.started
                    ) if self.contest1.started is not None else datetime.timedelta() 
                )} })
        self.assertEqual(payloads[1],
            { "token": str(evt1 + 1), "id": subid, "type": "submission-state",
             "data": {"submission_id": subid, "status": "starting"} })
        self.assertEqual(payloads[2],
            { "token": str(evt1 + 2), "id": subid, "type": "submission-state",
             "data": {"submission_id": subid, "status": "compiling"} })
        self.assertEqual(payloads[3],
            { "token": str(evt1 + 3), "id": subid, "type": "submission-state",
             "data": {"submission_id": subid, "status": "running"} })
        self.assertEqual(payloads[4],
            { "token": str(evt1 + 4), "id": subid, "type": "submission-state",
             "data": {"submission_id": subid, "status": "finished"} })
        self.assertEqual(payloads[5],
            { "token": str(evt1 + 5), "id": subid, "type": "judgements",
             "data": {"id": subid, "submission_id": subid, "judgement_type_id": "AC"} })
        self.assertEqual(payloads[6],
            { "token": str(evt1 + 6), "id": str(balloon.pk), "type": "balloons",
            "data": {"id": str(balloon.pk), "problem_id": str(problem.id), "account_id": str(self.team_user.pk), "status": "pending"} })