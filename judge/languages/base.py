
import os
import shutil
from typing import Callable, List, Tuple

import aiofiles

from judge.error import JudgeError
from sandbox.context import sandbox_open
from sandbox.result import SandboxResult
from sandbox.sandbox import Sandbox

from judge.telemetry import start_as_current_span, judge_logger

class Language:
    def language_name (self):
        raise NotImplementedError()

    def should_compile (self):
        return False
    async def compile(self, file: str, storage: str) -> Tuple[bool, SandboxResult]:
        raise NotImplementedError()
    
    def get_execution_command (self, filename: str):
        raise NotImplementedError()
    async def execute (self, file: str) -> "Tuple[ Sandbox, List[str] ]":
        with start_as_current_span("create_execution_sandbox") as span:
            span.set_attribute("executable:src", file)

            sandbox = await Sandbox.create_sandbox()

            filename = os.path.basename(file)
            filetar  = sandbox.path_relative_to_cwd(filename)

            await aiofiles.os.link( file, filetar )

            execution_command = self.get_execution_command(filename)

            span.set_attribute("executable:box", filename)
            span.set_attribute("executable:path", filetar)
            span.set_attribute("command", execution_command)

            return (
                sandbox,
                execution_command
            )

class CompiledLanguage (Language):
    def get_executable_name (self, filename: str):
        raise NotImplementedError()
    def get_compilation_command (self, fileexe: str, filename: str):
        raise NotImplementedError()
    def is_compilation_error_retcode (self, retcode: int):
        return retcode == 1
    def should_compile (self):
        return True
    async def compile(
            self,
            file: str,
            storage: str,
            before_run: "Callable[[Sandbox]]" = None) -> "Tuple[bool, SandboxResult]":
        with start_as_current_span("compile_executable") as span:
            async with sandbox_open() as sandbox:
                filename = os.path.basename(file)
                fileexe  = self.get_executable_name(filename)
                span.set_attribute("executable:source", file)
                span.set_attribute("executable:source:box", filename)
                span.set_attribute("executable:target", fileexe)

                await aiofiles.os.link(
                    file, sandbox.path_relative_to_cwd(filename)
                )
                
                if before_run is not None:
                    await before_run(sandbox)
                results = await sandbox.run_sandbox(
                    self.get_compilation_command(fileexe, filename),
                    time = 60,
                    wall_time = 60,
                    extra_time = 1,
                    num_process = 5,
                    memory = 1024 * 1024,
                    env_vars = [ ("PATH", "/usr/bin:/bin") ]
                )

                if results.process.returncode != 0:
                    # it is a compilation error (CE) if and only if
                    #  - isolate did not fail internally (e.g. retcode 1)
                    #  - and exitcode of program represents a CE 
                    if results.process.returncode == 1 \
                    and self.is_compilation_error_retcode(results.statistics.exit_code):
                        # standard compilation error
                        return False, results
                    
                    # huge compilation failure (e.g. isolate failure)
                    span.set_attribute("isolate:stdout", results.sandbox_stdout)
                    span.set_attribute("isolate:stderr", results.sandbox_stderr)
                    span.set_attribute("isolate:exitcode", results.process.returncode)
                    raise JudgeError( results )
                
                span.set_attribute("executable:storage", storage)

                shutil.move(
                    sandbox.path_relative_to_cwd(fileexe),
                    storage
                )

                return True, results
