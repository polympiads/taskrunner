
import asyncio
import os
from typing import TYPE_CHECKING, List

import aiofiles

from .telemetry import sandbox_logger

if TYPE_CHECKING: from sandbox.sandbox import Sandbox

class SandboxStatistics:
    time      : "float | None" = None
    wall_time : "float | None" = None

    exit_code   : "int | None" = None
    exit_signal : "int | None" = None

    max_memory : "int | None" = None
    status     : "str | None" = None

    killed  : "bool" = False
    message : "str | None" = None

    csw_forced    : "int | None" = None
    csw_voluntary : "int | None" = None

    cg_mem        : "int | None" = None
    cg_oom_killed : "bool" = False

    @staticmethod
    def read_from (lines: List[str]) -> "SandboxStatistics":
        stats = SandboxStatistics()

        for line in lines:
            line = line.strip()
            if len(line) == 0: continue

            try:
                key, value = line.split(":")

                match key:
                    case "cg-mem": stats.cg_mem = int(value)
                    case "cg-oom-killed": stats.cg_oom_killed = True
                    case "csw-forced": stats.csw_forced = int(value)
                    case "csw-voluntary": stats.csw_voluntary = int(value)
                    case "exitcode": stats.exit_code = int(value)
                    case "exitsig": stats.exit_signal = int(value)
                    case "killed": stats.killed = True
                    case "max-rss": stats.max_memory = int(value)
                    case "message": stats.message = value
                    case "status": stats.status = value
                    case "time": stats.time = float(value)
                    case "time-wall": stats.wall_time = float(value)
            except Exception as err:
                sandbox_logger.critical(
                    "Failure in sandbox statistics generation for line '%s', reason: %s",
                    line,
                    str(err)
                )

                raise err
        return stats

class SandboxResult:
    sandbox: "Sandbox"

    statistics: "SandboxStatistics"
    process: "asyncio.subprocess.Process"

    sandbox_stdout: bytes
    sandbox_stderr: bytes

    process_stdout: bytes | None = None
    process_stderr: bytes | None = None

    async def prepare (self, process_stdout_path: "str | None", process_stderr_path: "str | None"):
        if os.path.exists(process_stdout_path):
            async with aiofiles.open(process_stdout_path, "rb") as file:
                self.process_stdout = await file.read()
        if os.path.exists(process_stderr_path):
            async with aiofiles.open(process_stderr_path, "rb") as file:
                self.process_stderr = await file.read()
