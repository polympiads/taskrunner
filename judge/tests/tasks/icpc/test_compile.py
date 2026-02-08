"""
Test Cases for the compile celery task
"""

import unittest
from unittest.mock import patch

from config import MAX_LEN_ERROR_MESSAGE
from judge.languages import LanguageKind
from judge.languages.error import CompilationError
from judge.tasks.icpc.compile import CompilationResult, _compile_task, compile_task, CompilationInput
from storecli.error import DownloadError
from storecli.inmemory import InMemoryStorageClient

def custom_get_compilation_command (lang, exec, input):
    return [ "/usr/bin/bash", "-c", f"/usr/bin/echo Hello, World ! > {exec}" ]
def custom_get_compilation_command_fail (lang, exec, input):
    return [ "/usr/bin/exefail", "-c", f"/usr/bin/echo Hello, World ! > {exec}" ]

class TestICPCCompileTask (unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.inmemory_storage = InMemoryStorageClient( "/tmp" )

        self.patch_storage = patch("config.STORAGE_CLIENT", self.inmemory_storage)
        self.patch_storage.start()
    def tearDown(self):
        self.patch_storage.stop()
    
    async def test_download_error (self):
        with self.assertRaises(DownloadError):
            await _compile_task( CompilationInput( 0, "in.cpp", "in", LanguageKind.CPP_23, 1., 1. ) )
    async def test_compiles_properly (self):
        self.inmemory_storage.in_memory[ "in.cpp" ] = (b"int main () {}", ".cpp")
        compilation_result = await _compile_task( CompilationInput( 0, "in.cpp", "in", LanguageKind.CPP_23, 1., 1. ) )
        self.assertTrue(compilation_result.compilation_success)
        self.assertIsNone(compilation_result.error_message)

        assert "in" in self.inmemory_storage.in_memory
    @patch("judge.languages.cpp.CppLanguage.get_compilation_command", new = custom_get_compilation_command)
    async def test_uploaded_valid (self):
        self.inmemory_storage.in_memory[ "in.cpp" ] = (b"int main () {}", ".cpp")
        compilation_result = await _compile_task( CompilationInput( 0, "in.cpp", "in", LanguageKind.CPP_23, 1., 1. ) )
        self.assertTrue(compilation_result.compilation_success)
        self.assertIsNone(compilation_result.error_message)

        assert "in" in self.inmemory_storage.in_memory
        self.assertEqual(self.inmemory_storage.in_memory["in"], (b"Hello, World !\n", ""))
    async def test_compilation_fails_properly (self):
        self.inmemory_storage.in_memory[ "in.cpp" ] = (b"char main () {}", ".cpp")
        compilation_result = await _compile_task( CompilationInput( 0, "in.cpp", "in", LanguageKind.CPP_23, 1., 1. ) )
        self.assertFalse(compilation_result.compilation_success)
        self.assertIn(b"'::main' must return 'int'", compilation_result.error_message)
    @patch("judge.languages.cpp.CppLanguage.get_compilation_command", new = custom_get_compilation_command_fail)
    async def test_compilation_failure (self):
        self.inmemory_storage.in_memory[ "in.cpp" ] = (b"int main () {}", ".cpp")
        with self.assertRaises(CompilationError):
            await _compile_task( CompilationInput( 0, "in.cpp", "in", LanguageKind.CPP_23, 1., 1. ) )

    def test_result_truncated (self):
        error = b"a" * (2 * MAX_LEN_ERROR_MESSAGE)

        result = CompilationResult( False, error )
        self.assertFalse(result.compilation_success)
        self.assertEqual(result.error_message, (b"a" * MAX_LEN_ERROR_MESSAGE) + b" ...[truncated]")

class TestICPCCompileTaskSync (unittest.TestCase):
    def setUp(self):
        self.inmemory_storage = InMemoryStorageClient( "/tmp" )

        self.patch_storage = patch("config.STORAGE_CLIENT", self.inmemory_storage)
        self.patch_storage.start()
    def tearDown(self):
        self.patch_storage.stop()
    
    def test_download_error (self):
        with self.assertRaises(DownloadError):
            compile_task( CompilationInput( 0, "in.cpp", "in", LanguageKind.CPP_23, 1., 1. ) )
    def test_compiles_properly (self):
        self.inmemory_storage.in_memory[ "in.cpp" ] = (b"int main () {}", ".cpp")
        compilation_result = compile_task( CompilationInput( 0, "in.cpp", "in", LanguageKind.CPP_23, 1., 1. ) )
        self.assertTrue(compilation_result.compilation_success)
        self.assertIsNone(compilation_result.error_message)

        assert "in" in self.inmemory_storage.in_memory
    @patch("judge.languages.cpp.CppLanguage.get_compilation_command", new = custom_get_compilation_command)
    def test_uploaded_valid (self):
        self.inmemory_storage.in_memory[ "in.cpp" ] = (b"int main () {}", ".cpp")
        compilation_result = compile_task( CompilationInput( 0, "in.cpp", "in", LanguageKind.CPP_23, 1., 1. ) )
        self.assertTrue(compilation_result.compilation_success)
        self.assertIsNone(compilation_result.error_message)

        assert "in" in self.inmemory_storage.in_memory
        self.assertEqual(self.inmemory_storage.in_memory["in"], (b"Hello, World !\n", ""))
    def test_compilation_fails_properly (self):
        self.inmemory_storage.in_memory[ "in.cpp" ] = (b"char main () {}", ".cpp")
        compilation_result = compile_task( CompilationInput( 0, "in.cpp", "in", LanguageKind.CPP_23, 1., 1. ) )
        self.assertFalse(compilation_result.compilation_success)
        self.assertIn(b"'::main' must return 'int'", compilation_result.error_message)
    @patch("judge.languages.cpp.CppLanguage.get_compilation_command", new = custom_get_compilation_command_fail)
    def test_compilation_failure (self):
        self.inmemory_storage.in_memory[ "in.cpp" ] = (b"int main () {}", ".cpp")
        with self.assertRaises(CompilationError):
            compile_task( CompilationInput( 0, "in.cpp", "in", LanguageKind.CPP_23, 1., 1. ) )
