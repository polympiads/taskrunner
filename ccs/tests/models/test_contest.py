
import datetime
from zoneinfo import ZoneInfo

from django.test import TestCase

from ccs.models.contest import Contest
from ccs.models.visible import Visibility

from django.contrib.auth.models import User

class ContestTestCase (TestCase):
    def now (self):
        return datetime.datetime(
            2026, 2, 19,
            17, 47, 52, 681716,
            tzinfo = ZoneInfo("UTC")
        )
    def tomorrow (self):
        return datetime.datetime(
            2026, 2, 21,
            2, 47, 52, 681716,
            tzinfo = ZoneInfo("Asia/Tokyo")
        )

    def test_contest_display (self):
        usrA = User.objects.create_user("user",  "pwd")
        usrS = User.objects.create_superuser("super", "pwd")

        contest = Contest.objects.create(
            visibility = Visibility.PUBLIC,

            name        = "hc2-2025",
            formal_name = "Helvetic Coding Contest 2025",

            start_time           = self.now(),
            countdown_pause_time = None,

            duration = datetime.timedelta(hours = 5),

            scoreboard_freeze_duration = datetime.timedelta(hours = 1),
            scoreboard_thaw_time = self.tomorrow(),

            penalty_time = datetime.timedelta(minutes = 20)
        )

        self.assertEqual( contest.get_name(), "hc2-2025" )
        self.assertEqual( contest.get_formal_name(), "Helvetic Coding Contest 2025" )
        self.assertEqual( contest.get_start_time(), self.now() )
        self.assertEqual( contest.get_countdown_pause_time(), None )
        self.assertEqual( contest.get_duration(), datetime.timedelta(hours = 5) )
        self.assertEqual( contest.get_scoreboard_freeze_duration(), datetime.timedelta(hours = 1) )
        self.assertEqual( contest.get_scoreboard_thaw_time(), self.tomorrow() )
        self.assertEqual( contest.get_penalty_time(), datetime.timedelta(minutes = 20) )
        self.assertEqual( contest.get_scoreboard_type(), "pass-fail" )
        self.assertEqual( contest.get_display_json(), {
            "name": "hc2-2025",
            "id": str(contest.pk),
            "formal_name": "Helvetic Coding Contest 2025",
            "start_time": "2026-02-19T17:47:52.681Z",
            "duration": "5:00:00.000",
            "scoreboard_freeze_duration": "1:00:00.000",
            "scoreboard_thaw_time": "2026-02-21T02:47:52.681+09:00",
            "scoreboard_type": "pass-fail",
            "penalty_time": "0:20:00.000"
        })

        self.assertTrue (usrA.has_perm("contest.view", contest) )
        self.assertTrue (usrS.has_perm("contest.view", contest) )
        self.assertFalse(usrA.has_perm("contest.create"))
        self.assertTrue (usrS.has_perm("contest.create"))
        self.assertFalse(usrA.has_perm("contest.edit"))
        self.assertTrue (usrS.has_perm("contest.edit"))

        contest.scoreboard_thaw_time = contest.get_scoreboard_thaw_time().astimezone( ZoneInfo("Europe/Paris") )
        contest.start_time = contest.get_start_time().astimezone( ZoneInfo("America/New_York") )
        contest.formal_name = None
        contest.visibility = Visibility.PRIVATE
        contest.save()
        
        self.assertEqual( contest.get_display_json(), {
            "name": "hc2-2025",
            "id": str(contest.pk),
            "formal_name": "hc2-2025",
            "start_time": "2026-02-19T12:47:52.681-05:00",
            "duration": "5:00:00.000",
            "scoreboard_freeze_duration": "1:00:00.000",
            "scoreboard_thaw_time": "2026-02-20T18:47:52.681+01:00",
            "scoreboard_type": "pass-fail",
            "penalty_time": "0:20:00.000"
        })
        
        self.assertFalse( usrA.has_perm("contest.view", contest) )
        self.assertTrue( usrS.has_perm("contest.view", contest) )
        self.assertFalse(usrA.has_perm("contest.create"))
        self.assertTrue (usrS.has_perm("contest.create"))
        self.assertFalse(usrA.has_perm("contest.edit"))
        self.assertTrue (usrS.has_perm("contest.edit"))
