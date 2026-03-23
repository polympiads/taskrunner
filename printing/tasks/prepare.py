
from asyncio import StreamReader
import asyncio.subprocess
import os
import tempfile
from typing import List

from django.conf import settings
from taskrunner.celery import judge_app

from asgiref.sync import async_to_sync, sync_to_async

def template_path ():
    return os.path.join(os.path.dirname(__file__), "latex_template.tex")
def read_template ():
    with open(template_path(), "r") as file:
        return file.read()

LATEX_TEMPLATE = read_template()

@judge_app.task
def prepare_pdf_print (print_id: int):
    return async_to_sync(_prepare_pdf_print)(print_id)

async def safe_communicate (process: asyncio.subprocess.Process, limit = 64 * 1024):
    stdout_chunks: "List[bytes]" = []
    stderr_chunks: "List[bytes]" = []

    current_total = 0

    async def read_stream (stream, storage: "List[bytes]"):
        nonlocal current_total
        
        while True:
            chunk = await stream.read(4096)
            if not chunk:
                break

            storage.append(chunk)
            current_total += len(chunk)

            if current_total > limit:
                await process.kill()
                raise Exception("Print Error: Latex output generated too big output.")
    
    await asyncio.gather(
        read_stream(process.stdout, stdout_chunks),
        read_stream(process.stderr, stderr_chunks)
    )

    return b"".join(stdout_chunks), b"".join(stderr_chunks)

async def _prepare_pdf_print (print_id: int):
    from printing.models import ContestPrint

    print = await ContestPrint.objects \
        .select_related("owner") \
        .select_related("contest") \
        .aget(pk = print_id)
    
    try:
        await sync_to_async(print.on_compiling)()

        code_file = await settings.STORAGE_CLIENT.download(print.code_location)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            teamname_file = os.path.join(tmpdir, "team_name")
            teamloc_file  = os.path.join(tmpdir, "team_location")
            tar_code_file = os.path.join(tmpdir, "input_code")
            template_file = os.path.join(tmpdir, "print.tex")
            res_pdf_file  = os.path.join(tmpdir, "print.pdf")
            res_err_file  = os.path.join(tmpdir, "err.txt")

            with open(teamname_file, "w") as file:
                if print.owner.first_name == "":
                    file.write(print.owner.username)
                else:
                    file.write(print.owner.first_name)
            with open(teamloc_file, "w") as file:
                file.write(print.owner.last_name)
            with open(tar_code_file, "wb") as dst_file:
                with open(code_file, "rb") as src_file:
                    dst_file.write(src_file.read())

            with open(template_file, "w") as template:
                template.write(LATEX_TEMPLATE)

            process = await asyncio.subprocess.create_subprocess_exec(
                "pdflatex",
                "-interaction=nonstopmode",
                "--no-shell-escape",
                "print.tex",
                
                cwd = tmpdir,
                
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await safe_communicate(process)

            if process.returncode == 0:
                pdf_location = settings.STORAGE_CLIENT.reserve()
                
                await settings.STORAGE_CLIENT.upload(res_pdf_file, pdf_location)
                await sync_to_async(print.on_ready)(pdf_location)
            else:
                with open(res_err_file, "wb") as file:
                    file.write(b"=== STDOUT ===\n")
                    file.write(stdout)
                    file.write(b"\n")
                    file.write(b"=== STDERR ===\n")
                    file.write(stderr)
                
                err_location = settings.STORAGE_CLIENT.reserve()
                
                await settings.STORAGE_CLIENT.upload(res_err_file, err_location)
                await sync_to_async(print.on_compile_error)(err_location)
    except Exception as exc:
        await sync_to_async(print.on_task_error)(str(exc))
        raise exc
