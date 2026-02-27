
import os
from typing import List
import unittest

import aiofiles

from judge.languages.base import CompiledLanguage, Language
from judge.tests.utils import assert_all_sandbox_freed
from sandbox.context import sandbox_open
from sandbox.sandbox import Sandbox
from judge.telemetry import start_as_current_span

class TestLanguage(unittest.IsolatedAsyncioTestCase):
    async def test_default_functions (self):
        lang = Language()
        with self.assertRaises(NotImplementedError):
            lang.language_name()
        with self.assertRaises(NotImplementedError):
            lang.get_execution_command("file")
        with self.assertRaises(NotImplementedError):
            x = lang.ccs_language_information
        with self.assertRaises(NotImplementedError):
            await lang.compile("file", "storage")
        self.assertFalse(lang.should_compile())

        lang = CompiledLanguage()
        self.assertTrue(lang.should_compile())
        with self.assertRaises(NotImplementedError):
            lang.get_compilation_command("exe", "file")
        with self.assertRaises(NotImplementedError):
            lang.get_executable_name("file")

class BaseLanguageTest:
    def __init__(self, language: Language, folder: str, ext: str, exe_ext: str = ""):
        self.language = language
        self.folder = folder
        self.ext = ext
        self.exe_ext = exe_ext
    
    def hello_world (self) -> str: raise NotImplementedError()
    def nplus1 (self) -> str: raise NotImplementedError()
    def aplusb (self) -> str: raise NotImplementedError()
    
    def name_hello_world (self) -> str: return "hello_world"
    def name_nplus1 (self) -> str: return "nplus1"
    def name_aplusb (self) -> str: return "aplusb"
    
    async def internal_execute (self, file: str, content: str):
        os.makedirs( os.path.dirname(file), exist_ok=True )

        async with aiofiles.open(file, "w") as fw:
            await fw.write(content)
        
        file_exe = os.path.splitext(file)[0]
        if self.exe_ext != "":
            file_exe = file_exe + "." + self.exe_ext

        file_tar = file # interpreter
        if self.language.should_compile():
            success, results, errstring = await self.language.compile(file, file_exe)
            assert success, results.sandbox_stdout + results.sandbox_stderr + results.process_stdout + results.process_stderr
            file_tar = file_exe # compiled 

        return await self.language.execute(file_tar)
    async def read_file (self, file: str):
        async with aiofiles.open(file, "r") as fr:
            return await fr.read()
        
    async def assertWorks (
                self,
                sandbox: Sandbox,
                command: List[str],
                input:    str = "",
                output:   str = "",
                exitcode: int = 0
            ):
        async with aiofiles.open(sandbox.path_relative_to_cwd("in.txt"), "w") as fw:
            await fw.write(input)
        
        results = await sandbox.run_sandbox(
            command,
            stdin = "in.txt",
            num_process = self.language.number_execution_processes(),
            directories = self.language.extra_execution_directories(),
            enable_simple_memory=self.language.enable_simple_memory(),
            enable_cgroup_memory=self.language.enable_cgroup_memory())
        self.assertEqual( results.statistics.exit_code, exitcode )
        self.assertEqual( 
            results.process_stdout,
            output
        )

    async def test_hello_world (self):
        with start_as_current_span("test_hello_world"):
            sb, cmd = await self.internal_execute(
                f"/app/progs/{self.folder}/{self.name_hello_world()}.{self.ext}",
                self.hello_world()
            )

            async with sandbox_open(sb):
                await self.assertWorks(sb, cmd, output = b"Hello, World !\n")

            await assert_all_sandbox_freed()
    async def test_nplus1 (self):
        with start_as_current_span("test_nplus1"):
            sb, cmd = await self.internal_execute(
                f"/app/progs/{self.folder}/{self.name_nplus1()}.{self.ext}",
                self.nplus1()
            )

            async with sandbox_open(sb):
                await self.assertWorks(sb, cmd, input = "2\n", output = b"3\n")
                await self.assertWorks(sb, cmd, input = "21\n", output = b"22\n")

            await assert_all_sandbox_freed()
    async def test_aplusb (self):
        with start_as_current_span("test_aplusb"):
            sb, cmd = await self.internal_execute(
                f"/app/progs/{self.folder}/{self.name_aplusb()}.{self.ext}",
                self.aplusb()
            )

            async with sandbox_open(sb):
                await self.assertWorks(sb, cmd, input = "2 3\n", output = b"5\n")
                await self.assertWorks(sb, cmd, input = "21 42\n", output = b"63\n")
                await self.assertWorks(sb, cmd, input = "-51 42\n", output = b"-9\n")

            await assert_all_sandbox_freed()

