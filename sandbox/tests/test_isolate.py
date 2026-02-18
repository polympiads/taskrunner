
import unittest

from django.test import override_settings

from sandbox.isolate import Isolate


class TestIsolate (unittest.TestCase):
    @override_settings(USE_CGROUPS=False)
    def test_base_command (self):
        self.assertEqual(
            Isolate.base_command( 42 ),
            [ "isolate", "--box-id=42" ]
        )

    @override_settings(USE_CGROUPS=False)
    def test_init_command (self):
        self.assertEqual(
            Isolate.init_command( 42 ),
            [ "isolate", "--box-id=42", "--init" ]
        )
    @override_settings(USE_CGROUPS=False)
    def test_cleanup_command (self):
        self.assertEqual(
            Isolate.cleanup_command( 42 ),
            [ "isolate", "--box-id=42", "--cleanup" ]
        )

    @override_settings(USE_CGROUPS=False)
    def test_run_command (self):
        self.assertEqual(
            Isolate.run_command(
                42,
                [ "python3", "main.py" ],
                "stat.txt",
                1.0, 2.0, 4.0, 420,
                "in.txt", "out.txt", "err.txt",
                4, [ ("PATH", "/usr/bin") ],
                [],
                True, True
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
    
    @override_settings(USE_CGROUPS=True)
    def test_cgroup_commands (self):
        self.assertEqual(
            Isolate.base_command( 42 ),
            [ "isolate", "--box-id=42", "--cg" ]
        )
        self.assertEqual(
            Isolate.init_command( 42 ),
            [ "isolate", "--box-id=42", "--cg", "--init" ]
        )
        self.assertEqual(
            Isolate.cleanup_command( 42 ),
            [ "isolate", "--box-id=42", "--cg", "--cleanup" ]
        )
        self.assertEqual(
            Isolate.run_command(
                42,
                [ "python3", "main.py" ],
                "stat.txt",
                1.0, 2.0, 4.0, 420,
                "in.txt", "out.txt", "err.txt",
                4, [ ("PATH", "/usr/bin") ],
                [ ("/usr/in", "/usr/out"), "/usr/both" ],
                True, True
            ),
            [
                "isolate", "--box-id=42", "--cg", "--run",
                "--meta=stat.txt",
                "--time=1.0", "--wall-time=2.0", "--extra-time=4.0",
                "--cg-mem=420", "--stdin=in.txt", "--stdout=out.txt",
                "--stderr=err.txt", "--processes=4", 
                "--dir=/usr/in=/usr/out", "--dir=/usr/both",
                "--env=PATH=/usr/bin", "--",
                "python3", "main.py"
            ]
        )
