
from django.test import TestCase

from balloons.models import BalloonStatus, balloon_status_to_string, balloon_status_from_string

class TestBalloonStatus (TestCase):
    def test_to_string (self):
        self.assertEqual(balloon_status_to_string(BalloonStatus.PENDING), "pending")
        self.assertEqual(balloon_status_to_string(BalloonStatus.TAKEN),   "taken")
        self.assertEqual(balloon_status_to_string(BalloonStatus.DROPPED), "dropped")

        with self.assertRaises(NotImplementedError):
            balloon_status_to_string(None)
    def test_from_string (self):
        self.assertEqual(balloon_status_from_string("pending"), BalloonStatus.PENDING)
        self.assertEqual(balloon_status_from_string("taken"),   BalloonStatus.TAKEN)
        self.assertEqual(balloon_status_from_string("dropped"), BalloonStatus.DROPPED)

        self.assertEqual(balloon_status_from_string("hello"), None)
