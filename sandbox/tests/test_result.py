
import unittest

from sandbox.result import SandboxStatistics

class TestSandboxStatistics (unittest.TestCase):
    def test_sample_lines (self):
        lines = [
            "time:0.001",
            "\ttime-wall:0.021",
            "max-rss:3644\r",
            "  csw-voluntary:2",
            "csw-forced:1",
            "exitcode:0  "
        ]

        stats = SandboxStatistics.read_from(lines)

        self.assertEqual(stats.time, 0.001)
        self.assertEqual(stats.wall_time, 0.021)
        self.assertEqual(stats.max_memory, 3644)
        self.assertEqual(stats.csw_voluntary, 2)
        self.assertEqual(stats.csw_forced, 1)
        self.assertEqual(stats.exit_code, 0)
        self.assertEqual(stats.killed, False)
        self.assertEqual(stats.cg_oom_killed, False)
        self.assertEqual(stats.message, None)
        self.assertEqual(stats.status, None)
        self.assertEqual(stats.exit_signal, None)
        self.assertEqual(stats.cg_mem, None)
    def test_time (self):
        stats = SandboxStatistics.read_from([ "time:0.52" ])

        self.assertEqual(stats.time, 0.52)
        self.assertEqual(stats.wall_time, None)
        self.assertEqual(stats.max_memory, None)
        self.assertEqual(stats.csw_voluntary, None)
        self.assertEqual(stats.csw_forced, None)
        self.assertEqual(stats.exit_code, None)
        self.assertEqual(stats.killed, False)
        self.assertEqual(stats.cg_oom_killed, False)
        self.assertEqual(stats.message, None)
        self.assertEqual(stats.status, None)
        self.assertEqual(stats.exit_signal, None)
        self.assertEqual(stats.cg_mem, None)
    def test_wall_time (self):
        stats = SandboxStatistics.read_from([ "time-wall:0.51" ])

        self.assertEqual(stats.time, None)
        self.assertEqual(stats.wall_time, 0.51)
        self.assertEqual(stats.max_memory, None)
        self.assertEqual(stats.csw_voluntary, None)
        self.assertEqual(stats.csw_forced, None)
        self.assertEqual(stats.exit_code, None)
        self.assertEqual(stats.killed, False)
        self.assertEqual(stats.cg_oom_killed, False)
        self.assertEqual(stats.message, None)
        self.assertEqual(stats.status, None)
        self.assertEqual(stats.exit_signal, None)
        self.assertEqual(stats.cg_mem, None)
    def test_max_memory (self):
        stats = SandboxStatistics.read_from([ "max-rss:3465" ])

        self.assertEqual(stats.time, None)
        self.assertEqual(stats.wall_time, None)
        self.assertEqual(stats.max_memory, 3465)
        self.assertEqual(stats.csw_voluntary, None)
        self.assertEqual(stats.csw_forced, None)
        self.assertEqual(stats.exit_code, None)
        self.assertEqual(stats.killed, False)
        self.assertEqual(stats.cg_oom_killed, False)
        self.assertEqual(stats.message, None)
        self.assertEqual(stats.status, None)
        self.assertEqual(stats.exit_signal, None)
        self.assertEqual(stats.cg_mem, None)

    def test_csw_voluntary (self):
        stats = SandboxStatistics.read_from([ "csw-voluntary:45" ])

        self.assertEqual(stats.time, None)
        self.assertEqual(stats.wall_time, None)
        self.assertEqual(stats.max_memory, None)
        self.assertEqual(stats.csw_voluntary, 45)
        self.assertEqual(stats.csw_forced, None)
        self.assertEqual(stats.exit_code, None)
        self.assertEqual(stats.killed, False)
        self.assertEqual(stats.cg_oom_killed, False)
        self.assertEqual(stats.message, None)
        self.assertEqual(stats.status, None)
        self.assertEqual(stats.exit_signal, None)
        self.assertEqual(stats.cg_mem, None)

    def test_csw_forced (self):
        stats = SandboxStatistics.read_from([ "csw-forced:42" ])

        self.assertEqual(stats.time, None)
        self.assertEqual(stats.wall_time, None)
        self.assertEqual(stats.max_memory, None)
        self.assertEqual(stats.csw_voluntary, None)
        self.assertEqual(stats.csw_forced, 42)
        self.assertEqual(stats.exit_code, None)
        self.assertEqual(stats.killed, False)
        self.assertEqual(stats.cg_oom_killed, False)
        self.assertEqual(stats.message, None)
        self.assertEqual(stats.status, None)
        self.assertEqual(stats.exit_signal, None)
        self.assertEqual(stats.cg_mem, None)
        
    def test_exit_code (self):
        stats = SandboxStatistics.read_from([ "exitcode:21" ])

        self.assertEqual(stats.time, None)
        self.assertEqual(stats.wall_time, None)
        self.assertEqual(stats.max_memory, None)
        self.assertEqual(stats.csw_voluntary, None)
        self.assertEqual(stats.csw_forced, None)
        self.assertEqual(stats.exit_code, 21)
        self.assertEqual(stats.killed, False)
        self.assertEqual(stats.cg_oom_killed, False)
        self.assertEqual(stats.message, None)
        self.assertEqual(stats.status, None)
        self.assertEqual(stats.exit_signal, None)
        self.assertEqual(stats.cg_mem, None)
        
    def test_killed (self):
        stats = SandboxStatistics.read_from([ "killed:1" ])

        self.assertEqual(stats.time, None)
        self.assertEqual(stats.wall_time, None)
        self.assertEqual(stats.max_memory, None)
        self.assertEqual(stats.csw_voluntary, None)
        self.assertEqual(stats.csw_forced, None)
        self.assertEqual(stats.exit_code, None)
        self.assertEqual(stats.killed, True)
        self.assertEqual(stats.cg_oom_killed, False)
        self.assertEqual(stats.message, None)
        self.assertEqual(stats.status, None)
        self.assertEqual(stats.exit_signal, None)
        self.assertEqual(stats.cg_mem, None)
        
    def test_cg_oom_killed (self):
        stats = SandboxStatistics.read_from([ "cg-oom-killed:1" ])

        self.assertEqual(stats.time, None)
        self.assertEqual(stats.wall_time, None)
        self.assertEqual(stats.max_memory, None)
        self.assertEqual(stats.csw_voluntary, None)
        self.assertEqual(stats.csw_forced, None)
        self.assertEqual(stats.exit_code, None)
        self.assertEqual(stats.killed, False)
        self.assertEqual(stats.cg_oom_killed, True)
        self.assertEqual(stats.message, None)
        self.assertEqual(stats.status, None)
        self.assertEqual(stats.exit_signal, None)
        self.assertEqual(stats.cg_mem, None)
        
    def test_message (self):
        stats = SandboxStatistics.read_from([ "message:TLE !" ])

        self.assertEqual(stats.time, None)
        self.assertEqual(stats.wall_time, None)
        self.assertEqual(stats.max_memory, None)
        self.assertEqual(stats.csw_voluntary, None)
        self.assertEqual(stats.csw_forced, None)
        self.assertEqual(stats.exit_code, None)
        self.assertEqual(stats.killed, False)
        self.assertEqual(stats.cg_oom_killed, False)
        self.assertEqual(stats.message, "TLE !")
        self.assertEqual(stats.status, None)
        self.assertEqual(stats.exit_signal, None)
        self.assertEqual(stats.cg_mem, None)
        
    def test_ (self):
        stats = SandboxStatistics.read_from([ "status:TO" ])

        self.assertEqual(stats.time, None)
        self.assertEqual(stats.wall_time, None)
        self.assertEqual(stats.max_memory, None)
        self.assertEqual(stats.csw_voluntary, None)
        self.assertEqual(stats.csw_forced, None)
        self.assertEqual(stats.exit_code, None)
        self.assertEqual(stats.killed, False)
        self.assertEqual(stats.cg_oom_killed, False)
        self.assertEqual(stats.message, None)
        self.assertEqual(stats.status, "TO")
        self.assertEqual(stats.exit_signal, None)
        self.assertEqual(stats.cg_mem, None)
    def test_exit_signal (self):
        stats = SandboxStatistics.read_from([ "exitsig:7" ])

        self.assertEqual(stats.time, None)
        self.assertEqual(stats.wall_time, None)
        self.assertEqual(stats.max_memory, None)
        self.assertEqual(stats.csw_voluntary, None)
        self.assertEqual(stats.csw_forced, None)
        self.assertEqual(stats.exit_code, None)
        self.assertEqual(stats.killed, False)
        self.assertEqual(stats.cg_oom_killed, False)
        self.assertEqual(stats.message, None)
        self.assertEqual(stats.status, None)
        self.assertEqual(stats.exit_signal, 7)
        self.assertEqual(stats.cg_mem, None)
        
    def test_cg_mem (self):
        stats = SandboxStatistics.read_from([ "cg-mem:42000" ])

        self.assertEqual(stats.time, None)
        self.assertEqual(stats.wall_time, None)
        self.assertEqual(stats.max_memory, None)
        self.assertEqual(stats.csw_voluntary, None)
        self.assertEqual(stats.csw_forced, None)
        self.assertEqual(stats.exit_code, None)
        self.assertEqual(stats.killed, False)
        self.assertEqual(stats.cg_oom_killed, False)
        self.assertEqual(stats.message, None)
        self.assertEqual(stats.status, None)
        self.assertEqual(stats.exit_signal, None)
        self.assertEqual(stats.cg_mem, 42000)

    """
    These are bugs that already happened in production
    """

    def test_proxy_message (self):
        stats = SandboxStatistics.read_from([ "message:Cannot run proxy, clone failed: Operation not permitted" ])
        
        self.assertEqual(stats.time, None)
        self.assertEqual(stats.wall_time, None)
        self.assertEqual(stats.max_memory, None)
        self.assertEqual(stats.csw_voluntary, None)
        self.assertEqual(stats.csw_forced, None)
        self.assertEqual(stats.exit_code, None)
        self.assertEqual(stats.killed, False)
        self.assertEqual(stats.cg_oom_killed, False)
        self.assertEqual(stats.message, "Cannot run proxy, clone failed: Operation not permitted")
        self.assertEqual(stats.status, None)
        self.assertEqual(stats.exit_signal, None)
        self.assertEqual(stats.cg_mem, None)

    def test_exit_code_invalid (self):
        with self.assertRaises(Exception):
            stats = SandboxStatistics.read_from([ "exitcode:string" ])
