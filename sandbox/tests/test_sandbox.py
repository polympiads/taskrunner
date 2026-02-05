
import unittest

from unittest.mock import AsyncMock, MagicMock, patch
from sandbox import Sandbox, IsolateError
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
    def tearDown(self):
        self.patcher.stop()
        self.patcher_logger.stop()
        self.patcher_swcs.stop()
        self.patcher_trace.stop()

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
