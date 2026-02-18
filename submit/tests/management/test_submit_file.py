
import os
from unittest.mock import patch
from django.conf import settings
from django.test import TransactionTestCase, override_settings

from judge.languages import LanguageKind
from judge.tests.languages.test_cpp import APLUSB_PROG as APLUSB_PROG_CPP
from judge.tests.languages.test_java import APLUSB_PROG as APLUSB_PROG_JAVA
from judge.tests.languages.test_python import APLUSB_PROG as APLUSB_PROG_PYTHON
from judge.tests.tasks.icpc.test_scheduler import eager_celery
from problems.models.problem import Problem
from django.core.management import call_command
from django.contrib.auth.models import User

from problems.tests.management.test_prepare_polygon_cmd import APLUSB_FILE
from problems.tests.tasks.polygon.test_prepare import get_test_package_location
from storecli.inmemory import InMemoryStorageClient
from submit.models.submission import Submission
from submit.models.verdict import SubmissionVerdict

from taskrunner.celery import judge_app

APLUSB_PROG_CPP_SMALL_TLE = """
#include <iostream>

int main () {
    int a, b;
    std::cin >> a >> b;
    volatile int u = 0;
    volatile int v = 0;
    for (int i = 0; i < 10 * 1000 * 1000; i ++) {
        u ++;
        v --;
    }
    std::cout << a + b + u + v << "\\n";
}
"""
APLUSB_PROG_CPP_SMALL_MLE = """
#include <iostream>

const int MAXN = 1024 * 1024;
int dp[MAXN];
int main () {
    int a, b;
    std::cin >> a >> b;
    for (int u = 0; u < MAXN; u += 2) {
        dp[u] = 1;
        dp[u + 1] = -1;
    }
    for (int u = 0; u < MAXN; u ++) a += dp[u];
    std::cout << a + b << "\\n";
}
"""

class TestSubmitFileManager (TransactionTestCase):
    def setUp(self):
        self.inmemory_storage = InMemoryStorageClient("/tmp")
        self.patch_storage = override_settings(STORAGE_CLIENT=self.inmemory_storage)
        self.patch_storage.__enter__()
    def tearDown(self):
        self.patch_storage.__exit__(None, None, None)

    def mkfile (self, file: str):
        return os.path.abspath(os.path.join(os.path.dirname(__file__), file))

    def test_submit_file_cpp_aplusb (self):
        problem = Problem.objects.create()
        user = User.objects.create()

        with eager_celery():
            call_command("prepare_polygon", problem.pk, APLUSB_FILE)
            problem = Problem.objects.get(pk = problem.pk)
            with open(self.mkfile("index.cpp"), "w") as file:
                file.write(APLUSB_PROG_CPP)
            call_command("submit_file", user.pk, problem.pk, self.mkfile("index.cpp"))
        
            self.assertEqual(len(Submission.objects.all()), 1)
            submission = Submission.objects.all()[0]
            self.assertEqual( submission.verdict, SubmissionVerdict.ACCEPTED )
    def test_submit_file_cpp_aplusb_doesnotexist (self):
        problem = Problem.objects.create()
        user = User.objects.create()

        with eager_celery():
            call_command("prepare_polygon", problem.pk, APLUSB_FILE)
            problem = Problem.objects.get(pk = problem.pk)
            with open(self.mkfile("index.cpp"), "w") as file:
                file.write(APLUSB_PROG_CPP)
            with self.assertRaises(FileNotFoundError):
                call_command("submit_file", user.pk, problem.pk, self.mkfile("index2.cpp"))
        
            self.assertEqual(len(Submission.objects.all()), 0)
    def test_submit_file_python_aplusb (self):
        problem = Problem.objects.create()
        user = User.objects.create()

        with eager_celery():
            call_command("prepare_polygon", problem.pk, APLUSB_FILE)
            problem = Problem.objects.get(pk = problem.pk)
            with open(self.mkfile("index.py"), "w") as file:
                file.write(APLUSB_PROG_PYTHON)
            call_command("submit_file", user.pk, problem.pk, self.mkfile("index.py"))
        
            self.assertEqual(len(Submission.objects.all()), 1)
            submission = Submission.objects.all()[0]
            self.assertEqual( submission.verdict, SubmissionVerdict.ACCEPTED )
    def test_submit_file_java_aplusb (self):
        problem = Problem.objects.create()
        user = User.objects.create()

        with eager_celery():
            call_command("prepare_polygon", problem.pk, APLUSB_FILE)
            problem = Problem.objects.get(pk = problem.pk)
            with open(self.mkfile("index.java"), "w") as file:
                file.write(APLUSB_PROG_JAVA)
            call_command("submit_file", user.pk, problem.pk, self.mkfile("index.java"))
        
            self.assertEqual(len(Submission.objects.all()), 1)
            submission = Submission.objects.all()[0]
            self.assertEqual( submission.verdict, SubmissionVerdict.ACCEPTED )
    def test_submit_file_unknown_extension_aplusb (self):
        problem = Problem.objects.create()
        user = User.objects.create()

        with eager_celery():
            call_command("prepare_polygon", problem.pk, APLUSB_FILE)
            problem = Problem.objects.get(pk = problem.pk)
            with open(self.mkfile("index.blblblbl"), "w") as file:
                file.write(APLUSB_PROG_PYTHON)
            with self.assertRaises(NotImplementedError):
                call_command("submit_file", user.pk, problem.pk, self.mkfile("index.blblblbl"))
        
            self.assertEqual(len(Submission.objects.all()), 0)




    def test_submit_file_cpp_aplusb_slow_but_ac (self):
        problem = Problem.objects.create()
        user = User.objects.create()

        with eager_celery():
            call_command("prepare_polygon", problem.pk, APLUSB_FILE)
            problem = Problem.objects.get(pk = problem.pk)
            with open(self.mkfile("index.cpp"), "w") as file:
                file.write(APLUSB_PROG_CPP_SMALL_TLE)
            call_command("submit_file", user.pk, problem.pk, self.mkfile("index.cpp"))
        
            self.assertEqual(len(Submission.objects.all()), 1)
            submission = Submission.objects.all()[0]
            self.assertEqual( submission.verdict, SubmissionVerdict.ACCEPTED )
    def test_submit_file_cpp_aplusb_mem_but_ac (self):
        problem = Problem.objects.create()
        user = User.objects.create()

        with eager_celery():
            call_command("prepare_polygon", problem.pk, APLUSB_FILE)
            problem = Problem.objects.get(pk = problem.pk)
            with open(self.mkfile("index.cpp"), "w") as file:
                file.write(APLUSB_PROG_CPP_SMALL_MLE)
            call_command("submit_file", user.pk, problem.pk, self.mkfile("index.cpp"))
        
            self.assertEqual(len(Submission.objects.all()), 1)
            submission = Submission.objects.all()[0]
            self.assertEqual( submission.verdict, SubmissionVerdict.ACCEPTED )
    @override_settings(WALL_TIME_ADDITIONAL = 0)
    def test_submit_file_aplusb_small_tle (self):
        problem = Problem.objects.create()
        user = User.objects.create()
        
        with eager_celery():
            call_command("prepare_polygon", problem.pk, get_test_package_location("a-plus-b-small-tle.zip"))
            problem = Problem.objects.get(pk = problem.pk)

            with open(self.mkfile("index.cpp"), "w") as file:
                file.write(APLUSB_PROG_CPP_SMALL_TLE)
            call_command("submit_file", user.pk, problem.pk, self.mkfile("index.cpp"))
            
            self.assertEqual(len(Submission.objects.all()), 1)
            submission = Submission.objects.all()[0]
            self.assertEqual( submission.verdict, SubmissionVerdict.TIME_LIMIT )
    def test_submit_file_aplusb_small_mle (self):
        problem = Problem.objects.create()
        user = User.objects.create()
        
        with eager_celery():
            call_command("prepare_polygon", problem.pk, get_test_package_location("a-plus-b-small-mle.zip"))
            problem = Problem.objects.get(pk = problem.pk)

            with open(self.mkfile("index.cpp"), "w") as file:
                file.write(APLUSB_PROG_CPP_SMALL_MLE)
            call_command("submit_file", user.pk, problem.pk, self.mkfile("index.cpp"))
            
            self.assertEqual(len(Submission.objects.all()), 1)
            submission = Submission.objects.all()[0]

            if settings.USE_CGROUPS:
                self.assertEqual( submission.verdict, SubmissionVerdict.MEM_LIMIT )
            else:
                self.assertEqual( submission.verdict, SubmissionVerdict.RUNTIME_ERROR )
