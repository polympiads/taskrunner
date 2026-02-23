
from django.test import TestCase

from ccs.models.visible import Visibility, is_public

class VisibilityTestCase (TestCase):
    def test_is_public (self):
        self.assertTrue (is_public(None, Visibility.PUBLIC))
        self.assertFalse(is_public(None, Visibility.PRIVATE))
