
import os

import asyncio
import aiofiles
import aiofiles.os

from typing import List, Tuple

from sandbox.error import IsolateError, SandboxDoubleFree, SandboxUseAfterFree
from sandbox.isolate import Isolate
from sandbox.manager import SandboxManager
from sandbox.result import SandboxResult, SandboxStatistics
from sandbox.subprocess import run_subprocess_command

from .telemetry import start_as_current_span, trace, sandbox_logger
from .manager   import SandboxManager

from django.conf import settings

class Sandbox:
    def __init__ (self, box_id: int, box_dir: str):
        self.box_id  = box_id
        self.box_dir = box_dir

    @staticmethod
    async def create_sandbox () -> "Sandbox":
        with start_as_current_span("sandbox.create") as span:
            manager : SandboxManager = SandboxManager.instance()
            box_id  : int = await manager.allocate_id()

            trace.get_current_span() \
                .add_event( f"Acquired box id {box_id}" )

            try:
                proc, stdout, stderr = await run_subprocess_command(
                    *Isolate.init_command( box_id ) )

                if proc.returncode != 0:
                    raise IsolateError( f"Could not create box with id {box_id}" )
                
                box_dir = stdout.decode().strip()

                trace.get_current_span().set_status(trace.StatusCode.OK)
                sandbox_logger.info(
                    "Successfully created sandbox with id %s (%s)",
                    box_id, box_dir )
                
                return Sandbox( 
                    box_id, 
                    box_dir
                )
            except Exception as err:
                trace.get_current_span().set_status(trace.StatusCode.ERROR)
                sandbox_logger.critical(
                    "Could not create sandbox with id %s",
                    box_id )

                await manager.free_id(box_id)      
                raise err
            
    async def free_sandbox (self, safe_delete = False):
        if self.box_id == -1:
            if safe_delete:
                return
            raise SandboxDoubleFree()
        
        with start_as_current_span("sandbox.free") as span:
            try:
                await run_subprocess_command( *Isolate.cleanup_command(self.box_id) )
            finally:
                manager : SandboxManager = SandboxManager.instance()
                await manager.free_id(self.box_id)
                self.box_id = -1

    def path_relative_to_cwd (self, path: str):
        if path.startswith("/"):
            return os.path.join( self.box_dir, "box", path[1:] )
        return os.path.join( self.box_dir, "box", path )
    def path_relative_to_chroot (self, path: str):
        if path.startswith("/"):
            return os.path.join( self.box_dir, path[1:] )
        return os.path.join( self.box_dir, path )

    async def prepare_for_stdin (self, out_of_box: str, inside_box: str):
        os.chmod(out_of_box, 0o644)
        await aiofiles.os.link(out_of_box, self.path_relative_to_cwd(inside_box))

    async def get_stat_file (self):
        await aiofiles.os.makedirs( settings.SANDBOX_RESULT_FOLDER, exist_ok = True )
        return os.path.join( settings.SANDBOX_RESULT_FOLDER, f"{self.box_id}.stat" )
    async def run_sandbox (
            self,
            command : List[str],

            time       : "float | None" = settings.DEFAULT_TIME_LIMIT,
            wall_time  : "float | None" = settings.DEFAULT_WALL_TIME,
            extra_time : "float | None" = settings.DEFAULT_EXTRA_TIME,

            memory : "int | None" = settings.DEFAULT_MEMORY_KB, 

            stdin:  "str | None" = None,
            stdout: "str | None" = "out.txt",
            stderr: "str | None" = "err.txt",

            num_process : "int | None" = None,
            env_vars : "List[Tuple[str, str]]" = []
        ):
        if self.box_id == -1:
            raise SandboxUseAfterFree()

        with start_as_current_span("sandbox.run") as span:
            try:
                stat_file = await self.get_stat_file()

                isolate_command = Isolate.run_command(
                    self.box_id,
                    command,
                    stat_file,
                    time, wall_time, extra_time,
                    memory,
                    stdin, stdout, stderr,
                    num_process, env_vars
                )
                
                proc, sb_stdout, sb_stderr = await run_subprocess_command(*isolate_command)
                
                result = SandboxResult()
                result.process = proc

                process_stdout_path = self.path_relative_to_cwd(stdout)
                process_stderr_path = self.path_relative_to_cwd(stderr)
                await result.prepare(
                    process_stdout_path,
                    process_stderr_path
                )

                result.sandbox = self
                result.sandbox_stdout = sb_stdout
                result.sandbox_stderr = sb_stderr

                stat_reader = await aiofiles.open(stat_file, "r")
                stat_text = await stat_reader.read()
                await stat_reader.close()
                result.statistics = SandboxStatistics.read_from(
                    stat_text.splitlines()
                )

                # TODO, detect if there was a failure at the isolate step
                #  (e.g. unpriviliged or something like that), by checking
                #  status in statistics and propagate info upwards

                sandbox_logger.info(
                    "Command %s finished (time=%s, mem=%s)",
                    command,
                    result.statistics.time,
                    result.statistics.max_memory,
                    extra = {
                        "isolate_command": isolate_command,

                        "time": result.statistics.time,
                        "wall_time": result.statistics.wall_time,
                        "memory": result.statistics.max_memory,

                        "stats" : stat_text
                    }
                )

                return result
            except Exception as err:
                sandbox_logger.critical(
                    "Could not run isolate command %s: %s",
                    isolate_command,
                    str(err)
                )

                raise err
