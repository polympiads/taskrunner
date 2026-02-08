
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

    def test_run_command (self):
        self.assertEqual(
            Isolate.run_command(
                42,
                [ "python3", "main.py" ],
                "stat.txt",
                1.0, 2.0, 4.0, 420,
                "in.txt", "out.txt", "err.txt",
                4, [ ("PATH", "/usr/bin") ]
            ),
            [
                "isolate", "--box-id=42", "--run",
                "--meta=stat.txt",
                "--time=1.0", "--wall-time=2.0", "--extra-time=4.0",
                "--mem=420", "--stdin=in.txt", "--stdout=out.txt",
                "--stderr=err.txt", "--processes=4", "--env=PATH=/usr/bin", "--",
                "python3", "main.py"
            ]
        )
