
import os
import shutil
from typing import TYPE_CHECKING, Callable, List, Tuple

import aiofiles

if TYPE_CHECKING:
    from ccs.feed.languages import LanguagesCCSJson
from judge.error import JudgeError
from sandbox.context import sandbox_open
from sandbox.isolate import Isolate
from sandbox.result import SandboxResult
from sandbox.sandbox import Sandbox

from judge.telemetry import start_as_current_span, judge_logger

class Language:
    def language_name (self):
        raise NotImplementedError()

    @property
    def extension (self) -> str:
        raise NotImplementedError()
    @property
    def ccs_language_information (self) -> "LanguagesCCSJson":
        raise NotImplementedError()

    def should_compile (self):
        return False
    async def compile(self, file: str, storage: str) -> "Tuple[bool, SandboxResult, str | None]":
        raise NotImplementedError()
    
    def extra_execution_directories (self) -> "List[Tuple[str, str] | str]":
        return []
    def number_execution_processes (self) -> int:
        return 1
    def enable_simple_memory (self) -> bool:
        return True
    def enable_cgroup_memory (self) -> bool:
        return True
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
    class FileFormatError (RuntimeError):
        pass

    def get_executable_name (self, filename: str):
        raise NotImplementedError()
    def get_source_code_filename (self, file: str) -> str:
        """
        Get the source filename for a given file.
         - For most languages, this is just equivalent to taking the basename of the file
         - In Java, if there is a public class X, then the filename should be X.java,
           otherwise we may use any filename
        """
        return os.path.basename(file)
    def get_compilation_command (self, fileexe: str, filename: str):
        raise NotImplementedError()
    def get_compilation_commands (self, fileexe: str, filename: str, file: str):
        return [ self.get_compilation_command(fileexe, filename) ]
    def extra_compilation_directories (self) -> "List[Tuple[str, str] | str]":
        return []
    def is_compilation_error_retcode (self, retcode: int):
        return retcode == 1
    def should_compile (self):
        return True
    async def compile(
            self,
            file: str,
            storage: str,
            before_run: "Callable[[Sandbox]]" = None) -> "Tuple[bool, SandboxResult, str | None]":
        with start_as_current_span("compile_executable") as span:
            async with sandbox_open() as sandbox:
                try:
                    filename = self.get_source_code_filename(file)
                except self.FileFormatError as err:
                    return False, None, str(err)
                fileexe  = self.get_executable_name(filename)
                span.set_attribute("executable:source", file)
                span.set_attribute("executable:source:box", filename)
                span.set_attribute("executable:target", fileexe)

                await aiofiles.os.link(
                    file, sandbox.path_relative_to_cwd(filename)
                )
                
                if before_run is not None:
                    await before_run(sandbox)
                
                try:
                    compilation_commands = self.get_compilation_commands(fileexe, filename, file)
                except self.FileFormatError as err:
                    return False, None, str(err)
                
                for compilation_command in compilation_commands:
                    results = await sandbox.run_sandbox(
                        compilation_command,
                        time = 60,
                        wall_time = 60,
                        extra_time = 1,
                        num_process = Isolate.MAX_NUMBER_PROCESS,
                        memory = None,
                        directories = self.extra_compilation_directories(),
                        env_vars = [ ("PATH", "/usr/bin:/bin") ]
                    )

                    if results.process.returncode != 0:
                        # it is a compilation error (CE) if and only if
                        #  - isolate did not fail internally (e.g. retcode 1)
                        #  - and exitcode of program represents a CE 
                        if results.process.returncode == 1 \
                        and self.is_compilation_error_retcode(results.statistics.exit_code):
                            # standard compilation error
                            return False, results, None
                        
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

                return True, results, None
