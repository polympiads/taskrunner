
import datetime
import json

from django.test import TransactionTestCase
from django.contrib.auth.models import User

from asgiref.sync import async_to_sync

from ccs.models.contest import ContestAccount, ContestRole
from ccs.models.eventfeed import EventFeed
from ccs.models.managers.contest import ContestManager
from ccs.models.visible import Visibility

class TestAccountFeed (TransactionTestCase):
    def setUp(self):
        self.contest = async_to_sync(ContestManager.acreate_contest)(
            name         = "hc2",
            duration     = datetime.timedelta(hours = 5),
            penalty_time = datetime.timedelta(minutes = 20),
            visibility   = Visibility.PUBLIC
        )

        self.team_user  = User.objects.create_user("team_user")
        self.team2_user = User.objects.create_user("team_user2", first_name = "A Determiner")
        self.judge_user = User.objects.create_user("judge_user")

        EventFeed.objects.all().delete()

    def test_add_judge (self):
        ContestManager.add_accounts(
            self.contest.pk, 
            [(self.judge_user, ContestRole.JUDGE)]
        )
        feed = list( EventFeed.objects.all() )
        self.assertEqual(len(feed), 1)
        self.assertEqual(
            json.loads(feed[0].full_payload),
            { "id": str(self.judge_user.pk), "token": str(feed[0].pk), "type": "accounts",
             "data": { "id": str(self.judge_user.pk), "username": self.judge_user.username, "type": "judge" } })
        self.assertEqual(feed[0].visibility, Visibility.PRIVATE)
        self.assertIsNone(feed[0].owner)
        
        accounts = list(ContestAccount.objects.all())
        self.assertEqual(len(accounts), 1)
        self.assertEqual(accounts[0].contest.pk, self.contest.pk)
        self.assertEqual(accounts[0].user.pk, self.judge_user.pk)
        self.assertEqual(accounts[0].role, ContestRole.JUDGE)
    def test_add_team (self):
        ContestManager.add_accounts(
            self.contest.pk, 
            [(self.team_user, ContestRole.TEAM)]
        )

        feed = list( EventFeed.objects.all() )
        self.assertEqual(len(feed), 2)
        self.assertEqual(
            json.loads(feed[0].full_payload),
            { "id": str(self.team_user.pk), "token": str(feed[0].pk), "type": "accounts",
             "data": { "id": str(self.team_user.pk), "username": self.team_user.username, "type": "team" } })
        self.assertEqual(
            json.loads(feed[1].full_payload),
            { "id": str(self.team_user.pk), "token": str(feed[1].pk), "type": "teams",
             "data": { "id": str(self.team_user.pk), "name": self.team_user.username } })
        self.assertEqual(feed[0].visibility, Visibility.PUBLIC)
        self.assertEqual(feed[1].visibility, Visibility.PUBLIC)
        self.assertIsNone(feed[0].owner)
        self.assertIsNone(feed[1].owner)
        
        accounts = list(ContestAccount.objects.all())
        self.assertEqual(len(accounts), 1)
        self.assertEqual(accounts[0].contest.pk, self.contest.pk)
        self.assertEqual(accounts[0].user.pk, self.team_user.pk)
        self.assertEqual(accounts[0].role, ContestRole.TEAM)
    def test_add_team_display_name (self):
        ContestManager.add_accounts(
            self.contest.pk, 
            [(self.team2_user, ContestRole.TEAM)]
        )

        feed = list( EventFeed.objects.all() )
        self.assertEqual(len(feed), 2)
        self.assertEqual(
            json.loads(feed[0].full_payload),
            { "id": str(self.team2_user.pk), "token": str(feed[0].pk), "type": "accounts",
             "data": { "id": str(self.team2_user.pk), "username": self.team2_user.username, "type": "team" } })
        self.assertEqual(
            json.loads(feed[1].full_payload),
            { "id": str(self.team2_user.pk), "token": str(feed[1].pk), "type": "teams",
             "data": { "id": str(self.team2_user.pk), "name": self.team2_user.username,
                      "display_name": self.team2_user.first_name } })
        self.assertEqual(feed[0].visibility, Visibility.PUBLIC)
        self.assertEqual(feed[1].visibility, Visibility.PUBLIC)
        self.assertIsNone(feed[0].owner)
        self.assertIsNone(feed[1].owner)
        
        accounts = list(ContestAccount.objects.all())
        self.assertEqual(len(accounts), 1)
        self.assertEqual(accounts[0].contest.pk, self.contest.pk)
        self.assertEqual(accounts[0].user.pk, self.team2_user.pk)
        self.assertEqual(accounts[0].role, ContestRole.TEAM)
    def test_cant_add_account_twice (self):
        ContestManager.add_accounts(
            self.contest.pk, 
            [
                (self.team_user, ContestRole.TEAM),
                (self.team2_user, ContestRole.TEAM),
                (self.judge_user, ContestRole.JUDGE)
            ]
        )
        with self.assertRaisesRegex(ValueError, "Accounts \\['team_user', 'team_user2', 'judge_user'\\] already have a role\\."):
            ContestManager.add_accounts(
                self.contest.pk, 
                [
                    (self.team_user, ContestRole.TEAM),
                    (self.team2_user, ContestRole.TEAM),
                    (self.judge_user, ContestRole.JUDGE)
                ]
            )
        with self.assertRaisesRegex(ValueError, "Accounts \\['team_user', 'judge_user'\\] already have a role\\."):
            ContestManager.add_accounts(
                self.contest.pk, 
                [
                    (self.team_user, ContestRole.TEAM),
                    (self.judge_user, ContestRole.JUDGE)
                ]
            )

class TestAccountFeedContestStarted (TestAccountFeed):
    def setUp(self):
        super().setUp()

        ContestManager.start_contest(self.contest.pk)
        EventFeed.objects.all().delete()
