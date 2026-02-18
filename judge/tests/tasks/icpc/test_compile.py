"""
Test Cases for the compile celery task
"""

import asyncio
import unittest
from unittest.mock import patch

from django.contrib.auth.models import User
import django.test
from django.conf import settings
from django.test import override_settings
from judge.languages import LanguageKind
from judge.error import JudgeError
from judge.tasks.icpc.compile import CompilationResult, _compile_task, compile_task, CompilationInput
from judge.tests.languages.test_java import MISSING_MAIN
from problems.models.problem import Problem
from storecli.error import DownloadError
from storecli.inmemory import InMemoryStorageClient
from submit.models.status import SubmissionStatus
from submit.models.submission import Submission
from submit.models.verdict import SubmissionVerdict

def custom_get_compilation_command (lang, exec, input):
    return [ "/usr/bin/bash", "-c", f"/usr/bin/echo Hello, World ! > {exec}" ]
def custom_get_compilation_command_fail (lang, exec, input):
    return [ "/usr/bin/exefail", "-c", f"/usr/bin/echo Hello, World ! > {exec}" ]

class TestICPCCompileTask (django.test.TransactionTestCase):
    def setUp(self):
        self.inmemory_storage = InMemoryStorageClient( "/tmp" )

        self.patch_storage = override_settings(STORAGE_CLIENT=self.inmemory_storage)
        self.patch_storage.__enter__()

        usr = User.objects.create_user( "user", password = "pass" )
        sub = Submission.objects.create(
            user = usr,
            problem = Problem.objects.create(problem_location = None),
            language = LanguageKind.CPP_23,

            code_location = "in.cpp",
            exec_location = "in"
        )

        self.pk = sub.pk
        
        self.assertSubmission(SubmissionStatus.STARTING, SubmissionVerdict.PENDING)
    def tearDown(self):
        self.patch_storage.__exit__(None, None, None)
    
    def assertSubmission (self, status, verdict):
        sub = Submission.objects.get( pk = self.pk )

        self.assertEqual(sub.status, status)
        self.assertEqual(sub.verdict, verdict)
    
    def test_download_error (self):
        with self.assertRaises(DownloadError):
            asyncio.run( _compile_task( CompilationInput( self.pk, "in.cpp", "in", LanguageKind.CPP_23, 1., 1. ) ) )
        self.assertSubmission(
            SubmissionStatus.FAILED, SubmissionVerdict.JUDGE_ERROR)
    def test_compiles_properly (self):
        self.inmemory_storage.in_memory[ "in.cpp" ] = (b"int main () {}", ".cpp")
        compilation_result = asyncio.run( _compile_task( CompilationInput( self.pk, "in.cpp", "in", LanguageKind.CPP_23, 1., 1. ) ) )
        self.assertTrue(compilation_result.compilation_success)
        self.assertIsNone(compilation_result.error_message)

        assert "in" in self.inmemory_storage.in_memory
        
        self.assertSubmission(
            SubmissionStatus.COMPILING, SubmissionVerdict.PENDING)
    @patch("judge.languages.cpp.CppLanguage.get_compilation_command", new = custom_get_compilation_command)
    def test_uploaded_valid (self):
        self.inmemory_storage.in_memory[ "in.cpp" ] = (b"int main () {}", ".cpp")
        compilation_result = asyncio.run( _compile_task( CompilationInput( self.pk, "in.cpp", "in", LanguageKind.CPP_23, 1., 1. ) ) )
        self.assertTrue(compilation_result.compilation_success)
        self.assertIsNone(compilation_result.error_message)

        assert "in" in self.inmemory_storage.in_memory
        self.assertEqual(self.inmemory_storage.in_memory["in"], (b"Hello, World !\n", ""))
        
        self.assertSubmission(
            SubmissionStatus.COMPILING, SubmissionVerdict.PENDING)
    def test_compilation_fails_properly (self):
        self.inmemory_storage.in_memory[ "in.cpp" ] = (b"char main () {}", ".cpp")
        compilation_result = asyncio.run( _compile_task( CompilationInput( self.pk, "in.cpp", "in", LanguageKind.CPP_23, 1., 1. ) ) )
        self.assertFalse(compilation_result.compilation_success)
        self.assertIn(b"'::main' must return 'int'", compilation_result.error_message)
        
        self.assertSubmission(
            SubmissionStatus.FINISHED, SubmissionVerdict.COMPILER_ERROR)
    @patch("judge.languages.cpp.CppLanguage.get_compilation_command", new = custom_get_compilation_command_fail)
    def test_compilation_failure (self):
        self.inmemory_storage.in_memory[ "in.cpp" ] = (b"int main () {}", ".cpp")
        with self.assertRaises(JudgeError):
            asyncio.run( _compile_task( CompilationInput( self.pk, "in.cpp", "in", LanguageKind.CPP_23, 1., 1. ) ) )
        
        self.assertSubmission(
            SubmissionStatus.FAILED, SubmissionVerdict.JUDGE_ERROR)
    def test_does_not_exist (self):
        self.inmemory_storage.in_memory[ "in.cpp" ] = (b"int main () {}", ".cpp")
        with self.assertRaises(Submission.DoesNotExist):
            asyncio.run( _compile_task( CompilationInput( self.pk + 1, "in.cpp", "in", LanguageKind.CPP_23, 1., 1. ) ) )

    def test_result_truncated (self):
        error = b"a" * (2 * settings.MAX_LEN_ERROR_MESSAGE)

        result = CompilationResult( False, error )
        self.assertFalse(result.compilation_success)
        self.assertEqual(result.error_message, (b"a" * settings.MAX_LEN_ERROR_MESSAGE) + b" ...[truncated]")

class TestICPCCompileTaskSync (django.test.TransactionTestCase):
    def setUp(self):
        self.inmemory_storage = InMemoryStorageClient( "/tmp" )

        self.patch_storage = override_settings(STORAGE_CLIENT=self.inmemory_storage)
        self.patch_storage.__enter__()
        
        usr = User.objects.create_user( "user", password = "pass" )
        sub = Submission.objects.create(
            user = usr,
            problem = Problem.objects.create(problem_location = None),
            language = LanguageKind.CPP_23,

            code_location = "in.cpp",
            exec_location = "in"
        )

        self.pk = sub.pk

        self.assertSubmission(SubmissionStatus.STARTING, SubmissionVerdict.PENDING)
    def tearDown(self):
        self.patch_storage.__exit__(None, None, None)
        
    def assertSubmission (self, status, verdict):
        sub = Submission.objects.get( pk = self.pk )

        self.assertEqual(sub.status, status)
        self.assertEqual(sub.verdict, verdict)
    
    def test_download_error (self):
        with self.assertRaises(DownloadError):
            compile_task( CompilationInput( self.pk, "in.cpp", "in", LanguageKind.CPP_23, 1., 1. ).serialize() )
        self.assertSubmission(
            SubmissionStatus.FAILED, SubmissionVerdict.JUDGE_ERROR)
    def test_compiles_properly (self):
        self.inmemory_storage.in_memory[ "in.cpp" ] = (b"int main () {}", ".cpp")
        compilation_result = CompilationResult.deserialize(
            compile_task( CompilationInput( self.pk, "in.cpp", "in", LanguageKind.CPP_23, 1., 1. ).serialize() ) )
        self.assertTrue(compilation_result.compilation_success)
        self.assertIsNone(compilation_result.error_message)

        assert "in" in self.inmemory_storage.in_memory
        self.assertSubmission(
            SubmissionStatus.COMPILING, SubmissionVerdict.PENDING)
    @patch("judge.languages.cpp.CppLanguage.get_compilation_command", new = custom_get_compilation_command)
    def test_uploaded_valid (self):
        self.inmemory_storage.in_memory[ "in.cpp" ] = (b"int main () {}", ".cpp")
        compilation_result = CompilationResult.deserialize(
            compile_task( CompilationInput( self.pk, "in.cpp", "in", LanguageKind.CPP_23, 1., 1. ).serialize() ) )
        self.assertTrue(compilation_result.compilation_success)
        self.assertIsNone(compilation_result.error_message)

        assert "in" in self.inmemory_storage.in_memory
        self.assertEqual(self.inmemory_storage.in_memory["in"], (b"Hello, World !\n", ""))
        self.assertSubmission(
            SubmissionStatus.COMPILING, SubmissionVerdict.PENDING)
    def test_compilation_fails_properly (self):
        self.inmemory_storage.in_memory[ "in.cpp" ] = (b"char main () {}", ".cpp")
        compilation_result = CompilationResult.deserialize(
            compile_task( CompilationInput( self.pk, "in.cpp", "in", LanguageKind.CPP_23, 1., 1. ).serialize() ) )
        self.assertFalse(compilation_result.compilation_success)
        self.assertIn(b"'::main' must return 'int'", compilation_result.error_message)
        self.assertSubmission(
            SubmissionStatus.FINISHED, SubmissionVerdict.COMPILER_ERROR)
    def test_java_compilation_fails_properly (self):
        self.inmemory_storage.in_memory[ "in.java" ] = (MISSING_MAIN.encode(), ".java")
        compilation_result = CompilationResult.deserialize(
            compile_task( CompilationInput( self.pk, "in.java", "in.jar", LanguageKind.JAVA, 1., 1. ).serialize() ) )
        self.assertFalse(compilation_result.compilation_success)
        self.assertIn("Could not find class with public static void main.", compilation_result.error_message)
        self.assertSubmission(
            SubmissionStatus.FINISHED, SubmissionVerdict.COMPILER_ERROR)
    @patch("judge.languages.cpp.CppLanguage.get_compilation_command", new = custom_get_compilation_command_fail)
    def test_compilation_failure (self):
        self.inmemory_storage.in_memory[ "in.cpp" ] = (b"int main () {}", ".cpp")
        with self.assertRaises(JudgeError):
            compile_task( CompilationInput( self.pk, "in.cpp", "in", LanguageKind.CPP_23, 1., 1. ).serialize() )
        self.assertSubmission(
            SubmissionStatus.FAILED, SubmissionVerdict.JUDGE_ERROR)

    def test_does_not_exist (self):
        self.inmemory_storage.in_memory[ "in.cpp" ] = (b"int main () {}", ".cpp")
        with self.assertRaises(Submission.DoesNotExist):
            compile_task( CompilationInput( self.pk + 1, "in.cpp", "in", LanguageKind.CPP_23, 1., 1. ).serialize() )
