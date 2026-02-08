"""
Task Runner :: ICPC Judge

This task is supposed to be the task
taking an input storage location and
compiling that using the correct
compilation language, storing it in the
output location.
"""

import asyncio
import os
import tempfile
import config

from judge.languages import LanguageKind, get_language, get_language_name
from judge.languages.error import CompilationError
from judge.telemetry import start_as_current_span
from storecli.error import DownloadError

class CompilationResult:
    compilation_success : bool
    error_message       : "str | None"
    def __init__(self, success: bool = True, error_message: "str | None" = None):
        self.compilation_success = success

        if error_message is not None and len(error_message) >= config.MAX_LEN_ERROR_MESSAGE:
            error_message = error_message[:config.MAX_LEN_ERROR_MESSAGE] + b" ...[truncated]"
        self.error_message = error_message

class CompilationInput:
    submission_id: int
    input_storage: str
    exec_storage:  str

    language_kind: LanguageKind

    max_time:      float
    max_wall_time: float

    def __init__(
            self,
            submission_id: str,
            
            input_storage: str,
            exec_storage: str,
            
            language_kind: LanguageKind,
            
            max_time: float,
            max_wall_time: float):
        self.submission_id = submission_id
        self.input_storage = input_storage
        self.exec_storage = exec_storage
        self.language_kind = language_kind
        self.max_time = max_time
        self.max_wall_time = max_wall_time
        
@config.judge_app.task
def compile_task (params: CompilationInput):
    return asyncio.run( _compile_task(params) )

async def _compile_task (params: CompilationInput) -> CompilationResult:
    with start_as_current_span(f"Submission.compile") as span:
        span.set_attribute("submission:id", params.submission_id)
        span.set_attribute("storage:code", params.input_storage)
        span.set_attribute("storage:exe", params.exec_storage)
        span.set_attribute("compilation:max_time", params.max_time)
        span.set_attribute("compilation:max_wall_time", params.max_wall_time)
        span.set_attribute("submission:lang", get_language_name( params.language_kind ))
        
        with start_as_current_span("download.code"):
            target_file = await config.STORAGE_CLIENT.download(params.input_storage)

        with tempfile.TemporaryDirectory() as tmpdirname:
            temporary_storage = os.path.join(tmpdirname, "storage")

            language = get_language( params.language_kind )

            success, results = await language.compile( target_file, temporary_storage )
            if not success:
                return CompilationResult(
                    False,
                    results.process_stdout
                  + results.process_stderr
                )

            with start_as_current_span("upload.exe"):
                await config.STORAGE_CLIENT.upload(temporary_storage, params.exec_storage)

            return CompilationResult()
