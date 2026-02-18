
import os
import unittest

from unittest.mock import AsyncMock, MagicMock, patch
from django.conf import settings
from django.test import override_settings
from sandbox import Sandbox, IsolateError
from sandbox.context import sandbox_open
from sandbox.error import SandboxDoubleFree, SandboxUseAfterFree
from sandbox.subprocess import run_subprocess_command
from opentelemetry import trace

class TestSandbox(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.patcher = patch('sandbox.manager.SandboxManager.instance')
        
        self.mock_mgr_instance = self.patcher.start()
        self.mock_manager = AsyncMock()
        self.mock_mgr_instance.return_value = self.mock_manager

        self.patcher_logger = patch('sandbox.sandbox.sandbox_logger')
        self.patcher_trace  = patch('sandbox.sandbox.trace')
        self.patcher_swcs   = patch('sandbox.sandbox.start_as_current_span')

        self.sandbox_logger = self.patcher_logger.start()
        self.trace = self.patcher_trace.start()
        self.start_as_current_span = self.patcher_swcs.start()

        self.trace.StatusCode = trace.StatusCode

        self.log_debug    = self.sandbox_logger.debug    = MagicMock()
        self.log_info     = self.sandbox_logger.info     = MagicMock()
        self.log_warn     = self.sandbox_logger.warn     = MagicMock()
        self.log_danger   = self.sandbox_logger.danger   = MagicMock()
        self.log_critical = self.sandbox_logger.critical = MagicMock()

        self.current_span = self.trace.get_current_span.return_value = MagicMock()

        self.set_status = self.current_span.set_status = MagicMock()

        self.override_cgroup = override_settings(USE_CGROUPS=False)
        self.override_cgroup.__enter__()
    def tearDown(self):
        self.patcher.stop()
        self.patcher_logger.stop()
        self.patcher_swcs.stop()
        self.patcher_trace.stop()

        self.override_cgroup.__exit__(None, None, None)

    @patch('sandbox.sandbox.run_subprocess_command')
    async def test_create_sandbox_success(self, mock_run_cmd):
        self.mock_manager.allocate_id.return_value = 10

        mock_proc = MagicMock(returncode=0)
        mock_run_cmd.return_value = (mock_proc, b"/var/lib/isolate/10/box\n", b"")
    
        sandbox = await Sandbox.create_sandbox()

        args, _ = mock_run_cmd.call_args
        self.assertEqual(list(args), [ "isolate", "--box-id=10", "--init" ])

        self.assertIsInstance(sandbox, Sandbox)
        self.assertEqual(sandbox.box_id, 10)
        self.assertEqual(sandbox.box_dir, "/var/lib/isolate/10/box")

        self.start_as_current_span.assert_called_once_with("sandbox.create")
        self.set_status.assert_called_once_with(trace.StatusCode.OK)
        
        self.log_debug.assert_not_called()
        self.log_info.assert_called_once_with(
            "Successfully created sandbox with id %s (%s)", 10, "/var/lib/isolate/10/box"
        )
        self.log_warn.assert_not_called()
        self.log_danger.assert_not_called()
        self.log_critical.assert_not_called()

    @patch('sandbox.sandbox.run_subprocess_command')
    async def test_create_sandbox_isolate_failure(self, mock_run_cmd):
        self.mock_manager.allocate_id.return_value = 11
        
        mock_proc = MagicMock(returncode=1)
        mock_run_cmd.return_value = (mock_proc, b"", b"error")

        with self.assertRaises(IsolateError):
            await Sandbox.create_sandbox()

        args, _ = mock_run_cmd.call_args
        self.assertEqual(list(args), [ "isolate", "--box-id=11", "--init" ])

        self.mock_manager.free_id.assert_awaited_with(11)
        
        self.start_as_current_span.assert_called_once_with("sandbox.create")
        self.set_status.assert_called_once_with(trace.StatusCode.ERROR)
        self.log_debug.assert_not_called()
        self.log_info.assert_not_called()
        self.log_warn.assert_not_called()
        self.log_danger.assert_not_called()
        self.log_critical.assert_called_once_with(
            "Could not create sandbox with id %s", 11 )

    async def test_free_sandbox(self):
        sb = Sandbox(box_id=5, box_dir="/tmp/box")
        
        with patch('sandbox.sandbox.run_subprocess_command', new_callable=AsyncMock) as mock_run:
            await sb.free_sandbox()
            
            args, _ = mock_run.call_args
            self.assertEqual(list(args), [ "isolate", "--box-id=5", "--cleanup" ])
            
            self.mock_manager.free_id.assert_awaited_with(5)

        self.start_as_current_span.assert_called_once_with("sandbox.free")
        self.log_debug.assert_not_called()
        self.log_info.assert_not_called()
        self.log_warn.assert_not_called()
        self.log_danger.assert_not_called()
        self.log_critical.assert_not_called()
    async def test_free_sandbox_twice(self):
        sb = Sandbox(box_id=5, box_dir="/tmp/box")
        
        with patch('sandbox.sandbox.run_subprocess_command', new_callable=AsyncMock) as mock_run:
            await sb.free_sandbox()

            with self.assertRaises( SandboxDoubleFree ):
                await sb.free_sandbox()
    async def test_run_sandbox_freed (self):
        sb = Sandbox(box_id=5, box_dir="/tmp/box")
        
        with patch('sandbox.sandbox.run_subprocess_command', new_callable=AsyncMock) as mock_run:
            await sb.free_sandbox()

            with self.assertRaises( SandboxUseAfterFree ):
                await sb.run_sandbox([ "echo", "Hi !" ])

    async def test_path_relative_to_chroot (self):
        sb = Sandbox(box_id=5, box_dir="/tmp/box")

        self.assertEqual(sb.path_relative_to_chroot("a/b"),  os.path.join("/tmp/box", "a/b"))
        self.assertEqual(sb.path_relative_to_chroot("/a/b"), os.path.join("/tmp/box", "a/b"))
        self.assertEqual(sb.path_relative_to_chroot("a"),    os.path.join("/tmp/box", "a"))
        self.assertEqual(sb.path_relative_to_chroot("/a"),   os.path.join("/tmp/box", "a"))
    async def test_path_relative_to_cwd (self):
        sb = Sandbox(box_id=5, box_dir="/tmp/box")

        self.assertEqual(sb.path_relative_to_cwd("a/b"),  os.path.join("/tmp/box", "box", "a/b"))
        self.assertEqual(sb.path_relative_to_cwd("/a/b"), os.path.join("/tmp/box", "box", "a/b"))
        self.assertEqual(sb.path_relative_to_cwd("a"),    os.path.join("/tmp/box", "box", "a"))
        self.assertEqual(sb.path_relative_to_cwd("/a"),   os.path.join("/tmp/box", "box", "a"))
    async def test_prepare_for_stdin (self):
        with patch("os.chmod") as chmod:
            with patch("aiofiles.os.link") as link:
                sb = Sandbox(box_id=5, box_dir="/tmp/box")
                await sb.prepare_for_stdin( "/app/in.txt", "in.txt" )

                chmod.assert_called_once_with("/app/in.txt", 0o644)
                link.assert_awaited_once_with("/app/in.txt", os.path.join("/tmp/box", "box", "in.txt"))
    async def test_get_stat_file (self):
        with patch("aiofiles.os.makedirs") as makedirs:
            sb = Sandbox(box_id=5, box_dir="/tmp/box")

            stat_file = await sb.get_stat_file()

            self.assertEqual(stat_file, os.path.join(settings.SANDBOX_RESULT_FOLDER, "5.stat"))
            makedirs.assert_called_once_with(settings.SANDBOX_RESULT_FOLDER, exist_ok=True)
            
    @patch('sandbox.sandbox.run_subprocess_command')
    async def test_run_successfull_command (self, mock_run_cmd):
        with patch("sandbox.sandbox.Sandbox.get_stat_file", new_callable=AsyncMock) as get_stat_file:
            get_stat_file.return_value = "file/stat"

            mock_proc = MagicMock(returncode=0)
            mock_run_cmd.return_value = (mock_proc, b"OK (stdout)", b"OK (stderr)")

            with patch("aiofiles.open", new_callable=AsyncMock) as open:
                stat_open = open.return_value = MagicMock()
                stat_clse = stat_open.close = AsyncMock()
                stat_read = stat_open.read = AsyncMock(return_value="exitcode:0\ntime-wall:0.267\ntime:0.254\nmax-rss:256781\n")

                sb = Sandbox(5, "/tmp/box/5")
                sb_result = await sb.run_sandbox(
                    [ "./executable" ],
                    0.1,
                    0.2,
                    0.3,
                    4,
                    "5.txt",
                    "6.txt",
                    "../7.txt"
                )

                get_stat_file.assert_awaited_once_with()
                cmd = ('isolate',
                    '--box-id=5',
                    '--run', 
                    '--meta=file/stat',
                    '--time=0.1',
                    '--wall-time=0.2',
                    '--extra-time=0.3',
                    '--mem=4',
                    '--stdin=5.txt',
                    '--stdout=6.txt',
                    '--stderr=../7.txt',
                    '--',
                    './executable')
                mock_run_cmd.assert_awaited_once_with(*cmd)
                open.assert_awaited_once_with("file/stat", "r")
                stat_read.assert_awaited_once_with()
                stat_clse.assert_awaited_once_with()

                self.assertEqual(sb_result.process, mock_proc)

                # The out/err files do not exit so it returns None
                self.assertEqual(sb_result.process_stdout, None)
                self.assertEqual(sb_result.process_stderr, None)
                self.assertIs(sb_result.sandbox, sb)
                self.assertEqual(sb_result.sandbox_stdout, b"OK (stdout)")
                self.assertEqual(sb_result.sandbox_stderr, b"OK (stderr)")

                stats = sb_result.statistics
                self.assertEqual(stats.time, 0.254)
                self.assertEqual(stats.wall_time, 0.267)
                self.assertEqual(stats.max_memory, 256781)
                self.assertEqual(stats.csw_voluntary, None)
                self.assertEqual(stats.csw_forced, None)
                self.assertEqual(stats.exit_code, 0)
                self.assertEqual(stats.killed, False)
                self.assertEqual(stats.cg_oom_killed, False)
                self.assertEqual(stats.message, None)
                self.assertEqual(stats.status, None)
                self.assertEqual(stats.exit_signal, None)
                self.assertEqual(stats.cg_mem, None)

                self.log_debug.assert_not_called()
                self.log_info.assert_called_once_with(
                    "Command %s finished (time=%s, mem=%s)",
                    [ './executable' ],
                    0.254,
                    256781,
                    extra = {
                        "isolate_command": list(cmd),

                        "time": 0.254,
                        "wall_time": 0.267,
                        "memory": 256781,

                        "stats" : "exitcode:0\ntime-wall:0.267\ntime:0.254\nmax-rss:256781\n"
                    }
                )
                self.log_warn.assert_not_called()
                self.log_danger.assert_not_called()
                self.log_critical.assert_not_called()

                self.start_as_current_span.assert_called_once_with("sandbox.run")
    
    @patch('sandbox.sandbox.run_subprocess_command')
    async def test_run_failed_command (self, mock_run_cmd):
        with patch("sandbox.sandbox.Sandbox.get_stat_file", new_callable=AsyncMock) as get_stat_file:
            get_stat_file.return_value = "file/stat"

            mock_run_cmd.side_effect = IOError("Unexpected error")

            sb = Sandbox(5, "/tmp/box/5")
            with self.assertRaises(IOError):
                await sb.run_sandbox(
                    [ "./executable" ],
                    0.1,
                    0.2,
                    0.3,
                    4,
                    "5.txt",
                    "6.txt",
                    "../7.txt"
                )

            get_stat_file.assert_awaited_once_with()
            cmd = ('isolate',
                '--box-id=5',
                '--run', 
                '--meta=file/stat',
                '--time=0.1',
                '--wall-time=0.2',
                '--extra-time=0.3',
                '--mem=4',
                '--stdin=5.txt',
                '--stdout=6.txt',
                '--stderr=../7.txt',
                '--',
                './executable')
            mock_run_cmd.assert_awaited_once_with(*cmd)
            get_stat_file.assert_awaited_once_with()

            self.log_debug.assert_not_called()
            self.log_info.assert_not_called()
            self.log_warn.assert_not_called()
            self.log_danger.assert_not_called()
            self.log_critical.assert_called_once_with(
                "Could not run isolate command %s: %s",
                list(cmd),
                "Unexpected error"
            )
            
            self.start_as_current_span.assert_called_once_with("sandbox.run")
    
    async def test_double_free_safe (self):
        async with sandbox_open( Sandbox(-1, "/b/0") ):
            # If the sandbox_open isn't protected properly
            # This should raise an exception on async exit
            pass
