
import unittest
from unittest.mock import AsyncMock, Mock, patch

from sandbox.subprocess import run_subprocess_command

class TestSubprocess (unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.patch_exc = patch('asyncio.create_subprocess_exec')
        self.mock_exec = self.patch_exc.start()

        self.patch_trc = patch('opentelemetry.trace.get_current_span')
        self.mock_trac = self.patch_trc.start()
        self.mock_span = Mock()
        self.mock_trac.return_value = self.mock_span
        self.add_event = self.mock_span.add_event = Mock()
    def tearDown(self):
        self.patch_exc.stop()
        self.patch_trc.stop()

    def useReturnValue (self, retcode: int, stdout: bytes, stderr: bytes):
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (stdout, stderr)
        mock_proc.returncode = retcode

        self.mock_exec.return_value = mock_proc
    def useError (self, error):
        self.mock_exec.side_effect = error

    async def test_retcode_ok (self):
        self.useReturnValue(0, b"/box/7", b"")

        (proc, stdout, stderr) = await run_subprocess_command("isolate", "--init", "--box-id=7")

        self.assertEqual(stdout, b"/box/7")
        self.assertEqual(stderr, b"")

        self.assertEqual(proc.returncode, 0)

        self.add_event.assert_called_once_with(
            "Successfully ran command ('isolate', '--init', '--box-id=7') (retcode=0)",
            attributes={
                "stdout": b"/box/7",
                "stderr": b""
            }
        )
    async def test_retcode_bad (self):
        self.useReturnValue(1, b"", b"init failed")

        (proc, stdout, stderr) = await run_subprocess_command("isolate", "--init", "--box-id=7")

        self.assertEqual(stdout, b"")
        self.assertEqual(stderr, b"init failed")

        self.assertEqual(proc.returncode, 1)

        self.add_event.assert_called_once_with(
            "Successfully ran command ('isolate', '--init', '--box-id=7') (retcode=1)",
            attributes={
                "stdout": b"",
                "stderr": b"init failed"
            }
        )
    async def test_ioerror (self):
        self.useError( IOError() )

        with self.assertRaises(IOError):
            (proc, stdout, stderr) = await run_subprocess_command("isolate", "--init", "--box-id=7")

        self.add_event.assert_called_once_with(
            "Failed to run command ('isolate', '--init', '--box-id=7')" )
    async def test_exception (self):
        self.useError( Exception() )

        with self.assertRaises(Exception):
            (proc, stdout, stderr) = await run_subprocess_command("isolate", "--init", "--box-id=7")

        self.add_event.assert_called_once_with(
            "Failed to run command ('isolate', '--init', '--box-id=7')" )
