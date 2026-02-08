
import os
from typing import List
import unittest

import aiofiles

from judge.languages.python import PythonLanguage
from judge.tests.languages.test_base import BaseLanguageTest
from judge.tests.utils import assert_all_sandbox_freed, can_test_judge, skip_lang_tests
from sandbox.context import sandbox_open
from sandbox.sandbox import Sandbox

HELLO_WORLD_PROG = """
print("Hello, World !")
"""
NPLUS1_PROG = """
print(int(input()) + 1)
"""
APLUSB_PROG = """
a, b = list(map(int, input().split()))
print(a + b)
"""

@skip_lang_tests()
class TestPythonLanguage (unittest.IsolatedAsyncioTestCase, BaseLanguageTest):
    def __init__(self, methodName = "runTest"):
        super().__init__(methodName)
        BaseLanguageTest.__init__(
            self,
            PythonLanguage(),
            "python",
            "py"
        )

    def hello_world(self):
        return HELLO_WORLD_PROG
    def nplus1(self):
        return NPLUS1_PROG
    def aplusb(self):
        return APLUSB_PROG
