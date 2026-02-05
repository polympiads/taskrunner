
import unittest

from sandbox.isolate import Isolate


class TestIsolate (unittest.TestCase):
    def test_base_command (self):
        self.assertEqual(
            Isolate.base_command( 42 ),
            [ "isolate", "--box-id=42" ]
        )

    def test_init_command (self):
        self.assertEqual(
            Isolate.init_command( 42 ),
            [ "isolate", "--box-id=42", "--init" ]
        )
    def test_cleanup_command (self):
        self.assertEqual(
            Isolate.cleanup_command( 42 ),
            [ "isolate", "--box-id=42", "--cleanup" ]
        )
