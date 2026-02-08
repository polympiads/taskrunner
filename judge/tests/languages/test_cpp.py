
import os
from typing import List
import unittest

import aiofiles

from judge.languages.cpp import GNU_GPP_23
from judge.languages.python import PythonLanguage
from judge.tests.languages.test_base import BaseLanguageTest
from judge.tests.utils import assert_all_sandbox_freed, can_test_judge, skip_lang_tests
from sandbox.context import sandbox_open
from sandbox.sandbox import Sandbox

HELLO_WORLD_PROG = """
#include <iostream>

int main () {
    std::cout << "Hello, World !\\n";
}
"""
NPLUS1_PROG = """
#include <iostream>

int main () {
    int N;
    std::cin >> N;
    std::cout << N + 1 << "\\n";
}
"""
APLUSB_PROG = """
#include <iostream>

int main () {
    int a, b;
    std::cin >> a >> b;
    std::cout << a + b << "\\n";
}
"""

@skip_lang_tests()
class TestCppLanguage (unittest.IsolatedAsyncioTestCase, BaseLanguageTest):
    def __init__(self, methodName = "runTest"):
        super().__init__(methodName)

        BaseLanguageTest.__init__(
            self,
            GNU_GPP_23,
            "cpp23",
            "cpp"
        )

    def hello_world(self):
        return HELLO_WORLD_PROG
    def nplus1(self):
        return NPLUS1_PROG
    def aplusb(self):
        return APLUSB_PROG
