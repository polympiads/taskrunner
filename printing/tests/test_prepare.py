import asyncio
from datetime import timedelta
import hashlib
import json
import os
from typing import Callable
from unittest.mock import AsyncMock, patch

from django.test import TransactionTestCase, override_settings

from ccs.models.contest import Contest
from ccs.models.eventfeed import EventFeed
from ccs.models.managers.contest import ContestManager
from ccs.models.visible import Visibility
from judge.tests.languages.test_cpp import APLUSB_PROG
from judge.tests.tasks.icpc.test_scheduler import eager_celery
from printing.models import ContestPrint, PrintStatus
from storecli.inmemory import InMemoryStorageClient
from django.contrib.auth.models import User

class MockStream:
    def __init__ (self, stream: bytes):
        self.__stream = stream
        self.__offset = 0
    async def read (self, size: int):
        self.__offset += size
        return self.__stream[self.__offset - size:self.__offset]
class MockProcess:
    def __init__ (self, status_code: int, stdout: bytes = b"", stderr: bytes = b""):
        self.__status_code = status_code
        self.__stdout = stdout
        self.__stderr = stderr

        self.returncode = status_code

        self.stdout = MockStream(stdout)
        self.stderr = MockStream(stderr)
    async def kill (self):
        return
    
def mock_create_subprocess_exec (file_output: "bytes | Callable[[str], bytes]", file_target: str, mock_proc: MockProcess):
    async def _mock_create_subprocess_exec (*args, cwd = "", **kwargs):
        with open(os.path.join(cwd, file_target), "wb") as file:
            if isinstance(file_output, bytes):
                file.write(file_output)
            else: file.write(file_output(cwd))
        return mock_proc
    return _mock_create_subprocess_exec

def mock_pdflatex (cwd: str):
    result = []
    with open(os.path.join(cwd, "team_name"), "rb") as file:
        result.append(b"TEAM NAME: " + file.read())
    with open(os.path.join(cwd, "team_location"), "rb") as file:
        result.append(b"TEAM LOC: " + file.read())
    result.append(b"")
    with open(os.path.join(cwd, "input_code"), "rb") as file:
        result.append(file.read())

    return b"\n".join(result)

class PrintTaskTestCase (TransactionTestCase):
    def setUp(self):
        self.contest1 = asyncio.run( ContestManager.acreate_contest(
            name         = "pubct",
            duration     = timedelta(hours=5),
            penalty_time = timedelta(minutes = 20),
            visibility   = Visibility.PUBLIC
        ) )
        self.storage_client = InMemoryStorageClient("/tmp")
        self.new_settings = override_settings(
            ROOT_URLCONF="ccs.urls",            
            MIDDLEWARE = [
                'django.middleware.security.SecurityMiddleware',
                'ccs.auth.middleware.HeaderSessionMiddleware',
                'django.middleware.common.CommonMiddleware',
                'django.middleware.csrf.CsrfViewMiddleware',
                'django.contrib.auth.middleware.AuthenticationMiddleware',
                'django.contrib.messages.middleware.MessageMiddleware',
                'django.middleware.clickjacking.XFrameOptionsMiddleware',
            ],
            STORAGE_CLIENT = self.storage_client
        )
        self.new_settings.__enter__()

        EventFeed.objects.all().delete()
    def tearDown(self):
        self.new_settings.__exit__(None, None, None)
    
    def test_works_with_simple (self):
        user = User.objects.create(
            username = "user1",
            password = "password",
            first_name = "hello",
            last_name  = "world"
        )

        code_location = self.storage_client.reserve()
        self.storage_client.put(code_location, APLUSB_PROG.encode(), ".cpp")

        with eager_celery ():
            print = ContestPrint.objects.create_print(self.contest1, user, code_location)
            print.refresh_from_db()

            self.assertIsNone(print.err_location)
            self.assertIsNone(print.simple_error)
            self.assertIsNotNone(print.pdf_location)
            self.assertEqual(print.code_location, code_location)
            self.assertEqual(print.contest, self.contest1)
            self.assertEqual(print.owner.pk, user.pk)
            self.assertEqual(print.status, PrintStatus.READY)

            feed = list(EventFeed.objects.all())
            for x in feed:
                self.assertEqual(x.visibility, Visibility.PRIVATE)
                self.assertEqual(x.owner.pk, user.pk)
            self.assertEqual(len(feed), 3)
            self.assertEqual(
                json.loads(feed[0].full_payload),
                { "type": "prints", "id": str(print.pk), "token": str(feed[0].pk),
                "data": { "id": str(print.pk), "owner_id": str(user.pk), "status": "pending",
                "code_href": f"/contests/{print.contest.pk}/prints/{print.pk}/download/code/" } })
            self.assertEqual(
                json.loads(feed[1].full_payload),
                { "type": "prints", "id": str(print.pk), "token": str(feed[0].pk + 1),
                "data": { "id": str(print.pk), "owner_id": str(user.pk), "status": "compiling",
                "code_href": f"/contests/{print.contest.pk}/prints/{print.pk}/download/code/" } })
            self.assertEqual(
                json.loads(feed[2].full_payload),
                { "type": "prints", "id": str(print.pk), "token": str(feed[0].pk + 2),
                "data": { "id": str(print.pk), "owner_id": str(user.pk), "status": "ready",
                "code_href": f"/contests/{print.contest.pk}/prints/{print.pk}/download/code/",
                "pdf_href" : f"/contests/{print.contest.pk}/prints/{print.pk}/download/pdf/" } })

            file_bytes, file_type = self.storage_client.in_memory[print.pdf_location]
            self.assertEqual(file_type, ".pdf")
            hex_digest = hashlib.sha256(file_bytes).hexdigest()

            with open("/app/example_simple.pdf", "wb") as file:
                file.write(file_bytes)

            # The compilation of the PDF is deterministic and does not depend on time
            # Because of the specifics of the LaTeX template. The PDF has been checked
            # By hand using python3 -m http.server in the docker test container.
            # If you change the test, please also change the hash and retest it.
            self.assertEqual(hex_digest, "e2f0c1b480542d505d741b37dabddae1c17dc787e8ea18bb00757160d7490d19")
    def test_works_with_multipages (self):
        user = User.objects.create(
            username = "user1",
            password = "password",
            first_name = "hello",
            last_name  = "world"
        )

        code_location = self.storage_client.reserve()
        with open("/app/ccs/tests/views/test_submit.py", "rb") as file:
            self.storage_client.put(code_location, file.read(), ".py")

        with eager_celery ():
            print = ContestPrint.objects.create_print(self.contest1, user, code_location)
            print.refresh_from_db()

            self.assertIsNone(print.err_location)
            self.assertIsNone(print.simple_error)
            self.assertIsNotNone(print.pdf_location)
            self.assertEqual(print.code_location, code_location)
            self.assertEqual(print.contest, self.contest1)
            self.assertEqual(print.owner.pk, user.pk)
            self.assertEqual(print.status, PrintStatus.READY)

            file_bytes, file_type = self.storage_client.in_memory[print.pdf_location]
            self.assertEqual(file_type, ".pdf")
            hex_digest = hashlib.sha256(file_bytes).hexdigest()

            with open("/app/example_multipage.pdf", "wb") as file:
                file.write(file_bytes)

            # The compilation of the PDF is deterministic and does not depend on time
            # Because of the specifics of the LaTeX template. The PDF has been checked
            # By hand using python3 -m http.server in the docker test container.
            # If you change the test, please also change the hash and retest it.
            self.assertEqual(hex_digest, "2966ac67a599449e2c706fd44f28588211a70b34f0596c90ce48d42cbc870a83")

    def test_mocked_works (self):
        mock_proc = MockProcess(status_code=0, stdout=b"gone well", stderr=b"")
        
        user = User.objects.create(
            username = "user1",
            password = "password",
            first_name = "hello",
            last_name  = "world"
        )

        with patch("asyncio.subprocess.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
            mock_exec.side_effect = mock_create_subprocess_exec(
                b"Hello, Done\n",
                "print.pdf",
                mock_proc
            )

            code_location = self.storage_client.reserve()
            self.storage_client.put(code_location, APLUSB_PROG.encode(), ".cpp")

            with eager_celery():
                print = ContestPrint.objects.create_print(self.contest1, user, code_location)
                print.refresh_from_db()
                
                self.assertIsNone(print.err_location)
                self.assertIsNone(print.simple_error)
                self.assertIsNotNone(print.pdf_location)
                self.assertEqual(print.code_location, code_location)
                self.assertEqual(print.contest, self.contest1)
                self.assertEqual(print.owner.pk, user.pk)
                self.assertEqual(print.status, PrintStatus.READY)

                self.assertEqual(
                    self.storage_client.in_memory[print.pdf_location][0],
                    b"Hello, Done\n",
                )
    def test_mocked_works_on_limit_stdout (self):
        mock_proc = MockProcess(status_code=0, stdout=b"a" * (32 * 1024), stderr=b"a" * (32 * 1024))
        
        user = User.objects.create(
            username = "user1",
            password = "password",
            first_name = "hello",
            last_name  = "world"
        )

        with patch("asyncio.subprocess.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
            mock_exec.side_effect = mock_create_subprocess_exec(
                b"Hello, Done\n",
                "print.pdf",
                mock_proc
            )

            code_location = self.storage_client.reserve()
            self.storage_client.put(code_location, APLUSB_PROG.encode(), ".cpp")

            with eager_celery():
                print = ContestPrint.objects.create_print(self.contest1, user, code_location)
                print.refresh_from_db()
                
                self.assertIsNone(print.err_location)
                self.assertIsNone(print.simple_error)
                self.assertIsNotNone(print.pdf_location)
                self.assertEqual(print.code_location, code_location)
                self.assertEqual(print.contest, self.contest1)
                self.assertEqual(print.owner.pk, user.pk)
                self.assertEqual(print.status, PrintStatus.READY)

                self.assertEqual(
                    self.storage_client.in_memory[print.pdf_location][0],
                    b"Hello, Done\n",
                )
    def test_mocked_works_above_limit_stdout (self):
        mock_proc = MockProcess(status_code=0, stdout=b"a" * (32 * 1024 + 1), stderr=b"a" * (32 * 1024))
        
        user = User.objects.create(
            username = "user1",
            password = "password",
            first_name = "hello",
            last_name  = "world"
        )

        with patch("asyncio.subprocess.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
            mock_exec.side_effect = mock_create_subprocess_exec(
                b"Hello, Done\n",
                "print.pdf",
                mock_proc
            )

            code_location = self.storage_client.reserve()
            self.storage_client.put(code_location, APLUSB_PROG.encode(), ".cpp")

            with eager_celery():
                with self.assertRaises(Exception):
                    ContestPrint.objects.create_print(self.contest1, user, code_location)
                
                print = ContestPrint.objects.all()[0]

                self.assertIsNone(print.err_location)
                self.assertEqual(print.simple_error, "Print Error: Latex output generated too big output.")
                self.assertIsNone(print.pdf_location)
                self.assertEqual(print.code_location, code_location)
                self.assertEqual(print.contest, self.contest1)
                self.assertEqual(print.owner.pk, user.pk)
                self.assertEqual(print.status, PrintStatus.ERROR)

            feed = list(EventFeed.objects.all())
            for x in feed:
                self.assertEqual(x.visibility, Visibility.PRIVATE)
                self.assertEqual(x.owner.pk, user.pk)
            self.assertEqual(len(feed), 3)
            self.assertEqual(
                json.loads(feed[0].full_payload),
                { "type": "prints", "id": str(print.pk), "token": str(feed[0].pk),
                "data": { "id": str(print.pk), "owner_id": str(user.pk), "status": "pending",
                "code_href": f"/contests/{print.contest.pk}/prints/{print.pk}/download/code/" } })
            self.assertEqual(
                json.loads(feed[1].full_payload),
                { "type": "prints", "id": str(print.pk), "token": str(feed[0].pk + 1),
                "data": { "id": str(print.pk), "owner_id": str(user.pk), "status": "compiling",
                "code_href": f"/contests/{print.contest.pk}/prints/{print.pk}/download/code/" } })
            self.assertEqual(
                json.loads(feed[2].full_payload),
                { "type": "prints", "id": str(print.pk), "token": str(feed[0].pk + 2),
                "data": { "id": str(print.pk), "owner_id": str(user.pk), "status": "error",
                "code_href": f"/contests/{print.contest.pk}/prints/{print.pk}/download/code/",
                "simple_error": "Print Error: Latex output generated too big output." } })
    def test_mocked_works_on_error (self):
        mock_proc = MockProcess(status_code=1, stdout=b"here is stdout", stderr=b"here is stderr")
        
        user = User.objects.create(
            username = "user1",
            password = "password",
            first_name = "hello",
            last_name  = "world"
        )

        with patch("asyncio.subprocess.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
            mock_exec.side_effect = mock_create_subprocess_exec(
                b"Hello, Done\n",
                "print.pdf",
                mock_proc
            )

            code_location = self.storage_client.reserve()
            self.storage_client.put(code_location, APLUSB_PROG.encode(), ".cpp")

            with eager_celery():
                print = ContestPrint.objects.create_print(self.contest1, user, code_location)
                print.refresh_from_db()

                self.assertIsNotNone(print.err_location)
                self.assertIsNone(print.simple_error)
                self.assertIsNone(print.pdf_location)
                self.assertEqual(print.code_location, code_location)
                self.assertEqual(print.contest, self.contest1)
                self.assertEqual(print.owner.pk, user.pk)
                self.assertEqual(print.status, PrintStatus.FAILURE)

                file_bytes, file_type = self.storage_client.in_memory[print.err_location]
                self.assertEqual(file_type, ".txt")
                self.assertEqual(
                    file_bytes.splitlines(),
                    [
                        b"=== STDOUT ===",
                        b"here is stdout",
                        b"=== STDERR ===",
                        b"here is stderr"
                    ]
                )

            feed = list(EventFeed.objects.all())
            for x in feed:
                self.assertEqual(x.visibility, Visibility.PRIVATE)
                self.assertEqual(x.owner.pk, user.pk)
            self.assertEqual(len(feed), 3)
            self.assertEqual(
                json.loads(feed[0].full_payload),
                { "type": "prints", "id": str(print.pk), "token": str(feed[0].pk),
                "data": { "id": str(print.pk), "owner_id": str(user.pk), "status": "pending",
                "code_href": f"/contests/{print.contest.pk}/prints/{print.pk}/download/code/" } })
            self.assertEqual(
                json.loads(feed[1].full_payload),
                { "type": "prints", "id": str(print.pk), "token": str(feed[0].pk + 1),
                "data": { "id": str(print.pk), "owner_id": str(user.pk), "status": "compiling",
                "code_href": f"/contests/{print.contest.pk}/prints/{print.pk}/download/code/" } })
            self.assertEqual(
                json.loads(feed[2].full_payload),
                { "type": "prints", "id": str(print.pk), "token": str(feed[0].pk + 2),
                "data": { "id": str(print.pk), "owner_id": str(user.pk), "status": "failure",
                "code_href": f"/contests/{print.contest.pk}/prints/{print.pk}/download/code/",
                "err_href": f"/contests/{print.contest.pk}/prints/{print.pk}/download/err/" } })

    def test_mocked_works_custom_pdflatex (self):
        mock_proc = MockProcess(status_code=0, stdout=b"gone well", stderr=b"")
        
        user = User.objects.create(
            username = "user1",
            password = "password",
            first_name = "hello",
            last_name  = "world"
        )

        with patch("asyncio.subprocess.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
            mock_exec.side_effect = mock_create_subprocess_exec(
                mock_pdflatex,
                "print.pdf",
                mock_proc
            )

            code_location = self.storage_client.reserve()
            self.storage_client.put(code_location, APLUSB_PROG.encode(), ".cpp")

            with eager_celery():
                print = ContestPrint.objects.create_print(self.contest1, user, code_location)
                print.refresh_from_db()
                
                self.assertIsNone(print.err_location)
                self.assertIsNone(print.simple_error)
                self.assertIsNotNone(print.pdf_location)
                self.assertEqual(print.code_location, code_location)
                self.assertEqual(print.contest, self.contest1)
                self.assertEqual(print.owner.pk, user.pk)
                self.assertEqual(print.status, PrintStatus.READY)

                self.assertEqual(
                    self.storage_client.in_memory[print.pdf_location][0].splitlines(),
                    [
                        b"TEAM NAME: hello",
                        b"TEAM LOC: world",
                        b""
                    ] + APLUSB_PROG.encode().splitlines()
                )
    def test_mocked_works_custom_pdflatex_no_display_and_no_loc (self):
        mock_proc = MockProcess(status_code=0, stdout=b"gone well", stderr=b"")
        
        user = User.objects.create(
            username = "user1",
            password = "password"
        )

        with patch("asyncio.subprocess.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
            mock_exec.side_effect = mock_create_subprocess_exec(
                mock_pdflatex,
                "print.pdf",
                mock_proc
            )

            code_location = self.storage_client.reserve()
            self.storage_client.put(code_location, APLUSB_PROG.encode(), ".cpp")

            with eager_celery():
                print = ContestPrint.objects.create_print(self.contest1, user, code_location)
                print.refresh_from_db()
                
                self.assertIsNone(print.err_location)
                self.assertIsNone(print.simple_error)
                self.assertIsNotNone(print.pdf_location)
                self.assertEqual(print.code_location, code_location)
                self.assertEqual(print.contest, self.contest1)
                self.assertEqual(print.owner.pk, user.pk)
                self.assertEqual(print.status, PrintStatus.READY)

                self.assertEqual(
                    self.storage_client.in_memory[print.pdf_location][0].splitlines(),
                    [
                        b"TEAM NAME: user1",
                        b"TEAM LOC: ",
                        b""
                    ] + APLUSB_PROG.encode().splitlines()
                )
