
from django.test import TestCase

from ccs.models.visible import Visibility, is_public, visibility_to_string

class VisibilityTestCase (TestCase):
    def test_is_public (self):
        self.assertTrue (is_public(None, Visibility.PUBLIC))
        self.assertFalse(is_public(None, Visibility.PRIVATE))
    def test_to_string (self):
        self.assertEqual(visibility_to_string(Visibility.PUBLIC),  'public')
        self.assertEqual(visibility_to_string(Visibility.PRIVATE), 'private')

        with self.assertRaises(NotImplementedError):
            visibility_to_string(None)
