
from unittest import TestCase
import unittest

from judge.languages.java import JavaLanguage
from judge.tests.languages.test_base import BaseLanguageTest
from judge.tests.utils import skip_lang_tests

TWO_MAINS = """
class Hello {
    public static void main(String[] args) {}
}
public class World {
    public static void main(String[] args) {}
}
"""
MISSING_MAIN = """
class HelloWorld {
    public static void main2 (String[] args) {}
}
"""

HELLO_WORLD_PROG = """
class HelloWorld {
    public static void main(String[] args) {
        System.out.println("Hello, World !");
    }
}
"""
NPLUS1_PROG = """
import java.util.Scanner;
class NPlus1 {
    public static void main(String[] args) {
        int N;
        Scanner sc = new Scanner(System.in);
        N = sc.nextInt();
        System.out.println(N + 1);
    }
}
"""
APLUSB_PROG = """
import java.util.Scanner;
class APlusB {
    public static void main(String[] args) {
        int A, B;
        Scanner sc = new Scanner(System.in);
        A = sc.nextInt();
        B = sc.nextInt();
        System.out.println(A + B);
    }
}
"""

class TestJavaEntrypointFinder (TestCase):
    def setUp(self):
        self.lang = JavaLanguage()
    def test_hello_world (self):
        self.assertEqual(
            self.lang.find_main_class(HELLO_WORLD_PROG.encode()), "HelloWorld")
    def test_two_entrypoints (self):
        with self.assertRaisesRegex(
                JavaLanguage.FileFormatError,
                "Multiple classes with public static void main: Hello, World"):
            self.lang.find_main_class(TWO_MAINS.encode())
    def test_missing_entrypoints (self):
        with self.assertRaisesRegex(
                JavaLanguage.FileFormatError,
                "Could not find class with public static void main."):
            self.lang.find_main_class(MISSING_MAIN.encode())

@skip_lang_tests()
class TestJavaLanguage (unittest.IsolatedAsyncioTestCase, BaseLanguageTest):
    def __init__(self, methodName = "runTest"):
        super().__init__(methodName)
        BaseLanguageTest.__init__(
            self,
            JavaLanguage(),
            "java",
            "java",
            "jar"
        )

    def hello_world(self):
        return HELLO_WORLD_PROG
    def nplus1(self):
        return NPLUS1_PROG
    def aplusb(self):
        return APLUSB_PROG

