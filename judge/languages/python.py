
import os
import aiofiles.os

from django.conf import settings
from judge.languages.base import Language
from sandbox.sandbox import Sandbox

class PythonLanguage (Language):
    def language_name(self):
        return "Python"
    async def compile(self, file: str, storage: str):
        return False
    
    def get_execution_command (self, filename: str):
        return [settings.PYTHON_EXECUTABLE, filename]
