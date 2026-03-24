
import argparse
import asyncio
import datetime
import json
import os
import tempfile
import time
from typing import Dict
import zipfile

from django.contrib.auth.models import User
from django.conf import settings
from django.core.management import BaseCommand, call_command

from ccs.models.contest import Contest, ContestProblem, ContestRole
from ccs.models.managers.contest import ContestManager
from ccs.models.visible import Visibility
from problems.models.preparation import Preparation, PreparationStatus
from problems.models.problem import Problem
from problems.telemetry import start_as_current_span
from submit.management.commands.submit_file import submit_file
from submit.models.submission import Submission
from submit.models.verdict import SubmissionVerdict

COMMAND_EPILOG = """
The archive should be a .zip file containing
 - A file feed.ndjson
   The first line of the file should be of the form
      {"start_time": unix start time in seconds, "duration": contest duration in seconds}
   The next lines all represent a submission and should be of the form
      [submission id, "VERDICT", "TEAM NAME", "PROBLEM LABEL", unix time of problem]
 - For each problem label X, there should be a .zip file inside the archive of the form X.*.zip
 - There should also be a folder submissions/
   For each submission ID, there should be a unique file submissions/id.*, the code of the submission
""".strip()

class Command (BaseCommand):
    help = "Replay content from an archive"
    
    def create_parser(self, prog_name, subcommand, **kwargs):
        parser = super().create_parser(prog_name, subcommand, **kwargs)
        parser.epilog = COMMAND_EPILOG
        parser.formatter_class = argparse.RawDescriptionHelpFormatter
        
        return parser
    def add_arguments(self, parser):
        parser.add_argument("file",       type=str, help="The archive to replay")
        parser.add_argument("--contest-id",  type=int, help="The id of the contest to use")
        parser.add_argument("--speedup",  default=1, type=float, help="The speedup to apply to the replay")
        parser.add_argument("--slow-threshold", default=30, type=float, help="Number of seconds before triggering too slow message")

    def local_call_command (self, command, *args, **kwargs):
        if self.verbosity == 3:
            print(f"Calling command '{command}' with", args, kwargs)
        return call_command(command, *args, **kwargs)

    def handle (self, file: str, contest_id: int, speedup: "float" = 1, slow_threshold: "float" = 30, verbosity: int = 0, *args, **kwargs):
        self.verbosity = verbosity
        
        if not os.path.exists(file):
            raise FileNotFoundError(f"The archive '{file}' does not exist.")
        
        contest = Contest.objects.get(pk = contest_id)

        os.makedirs( settings.TEMPDIR_STORAGE_LOCATION, exist_ok=True )

        with tempfile.TemporaryDirectory(prefix = settings.TEMPDIR_STORAGE_LOCATION, delete = False) as tmpdir:
            with zipfile.ZipFile(file, "r") as zip_ref:
                zip_ref.extractall(tmpdir)
            
            subfiles = os.listdir(tmpdir)
            pk_from_label: "Dict[str, int]" = {}
            for subfile in subfiles:
                if subfile == "submissions" or subfile == "feed.ndjson":
                    continue

                problem = Problem.objects.create()

                self.local_call_command(
                    "prepare_polygon",
                    problem.pk,
                    os.path.abspath( os.path.join(tmpdir, subfile) )
                )

                pb_label = subfile.split(".")[0]

                pk_from_label[pb_label] = problem.pk
                
                link = ContestProblem.objects.create(contest = contest, problem = problem, label = pb_label)

            for label, pk in pk_from_label.items():
                while True:
                    if verbosity >= 2:
                        print(f"Problem {label}: PENDING")
                    problem = Problem.objects.get(pk = pk)
                    preparation = Preparation.objects.get(problem = problem)

                    match preparation.status:
                        case PreparationStatus.PENDING:
                            pass
                        case PreparationStatus.RUNNING:
                            pass
                        case PreparationStatus.SUCCESS:
                            if verbosity >= 1:
                                print(f"Problem {label}: OK")
                            break
                        case PreparationStatus.FAILURE:
                            raise RuntimeError(f"Judge Error: Could not prepare problem {label}...")

                    time.sleep(1)

            with open(os.path.join(tmpdir, "feed.ndjson"), "r") as file:
                lines = list(map(json.loads, file.read().splitlines()))

                base_line = lines[0]
                submissions = lines[1:]
                
                duration = base_line["duration"]
                start_time = base_line["start_time"]
            
            submissions.sort(key = lambda u: u[4])

            local_start_time = time.time()
            print("Start contest...")
            ContestManager.start_contest(contest.pk)
            contest.refresh_from_db()

            to_inspect = []

            def get_team_user (team: str) -> User:
                users = list(User.objects.filter(username = team))
                if len(users) != 0:
                    return users[0]
                user = User.objects.create_user(team)
                ContestManager.add_accounts(contest.pk, [(user, ContestRole.TEAM)])
                return user
            def find_submission (code: str) -> "str | None":
                code = code + "."

                subdir = os.path.join(tmpdir, "submissions")
                for obj in os.listdir(subdir):
                    if obj.startswith(code):
                        return os.path.join(subdir, obj)
                
                print(f"Couldn't find submission {code}")
                return None

            def run_submission (submission):
                subid, verdict, team, problem, _ = submission
                subfile = find_submission(str(subid))
                
                team_user = get_team_user(team)
                problem   = Problem.objects.get(pk = pk_from_label[problem])
                subfile   = os.path.abspath(subfile)

                if verbosity >= 3:
                    print(f"Submit file [{team_user}, {problem}, {subfile}]")
                subpk = submit_file(
                    get_team_user(team),
                    problem,
                    os.path.abspath( subfile ),
                    contest
                )

                true_verdict = None
                match verdict:
                    case "OK": true_verdict = SubmissionVerdict.ACCEPTED
                    case "WRONG_ANSWER": true_verdict = SubmissionVerdict.WRONG_ANSWER
                    case "COMPILATION_ERROR": true_verdict = SubmissionVerdict.COMPILER_ERROR
                    case "MEMORY_LIMIT_EXCEEDED": true_verdict = SubmissionVerdict.MEM_LIMIT
                    case "TIME_LIMIT_EXCEEDED": true_verdict = SubmissionVerdict.TIME_LIMIT
                    case "RUNTIME_ERROR": true_verdict = SubmissionVerdict.RUNTIME_ERROR
                
                to_inspect.append((subpk, subid, true_verdict, time.time()))
            
            offset = 0
            while offset < len(submissions):
                if submissions[offset][4] - start_time <= (time.time() - local_start_time) * speedup:
                    try:
                        run_submission(submissions[offset])
                    except Exception as exc:
                        print(f"Error on submission {submissions[offset]}:", str(exc))

                    offset += 1
                    continue

                new_to_inspect = []
                for subpk, subid, verdict, ftime in to_inspect:
                    submission = Submission.objects.get(pk = subpk)

                    if submission.verdict == SubmissionVerdict.PENDING:
                        if ftime != -1 \
                        and datetime.datetime.fromtimestamp(ftime) \
                          + datetime.timedelta(seconds = slow_threshold) \
                         <= datetime.datetime.fromtimestamp( time.time() ):
                            if verbosity >= 0:
                                print(f"Submission {subid}: ABOVE SLOW THRESHOLD")
                            ftime = -1
                        new_to_inspect.append((subpk, subid, verdict, ftime))
                        continue
                    
                    if submission.verdict == verdict:
                        print(f"Submission {subid}: OK")
                        continue

                    print(f"Submission {subid}: WRONG {verdict} => {submission.verdict}")
                to_inspect = new_to_inspect

                time.sleep(0.1)
                
