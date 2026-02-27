
import os
from typing import TYPE_CHECKING
import aiofiles.os

from django.conf import settings
from judge.languages.base import Language
from sandbox.sandbox import Sandbox

if TYPE_CHECKING:
    from ccs.views.languages import LanguagesCCSJson

class PythonLanguage (Language):
    def language_name(self):
        return "Python"
    
    def get_execution_command (self, filename: str):
        return [settings.PYTHON_EXECUTABLE, filename]

    @property
    def ccs_language_information (self) -> "LanguagesCCSJson":
        return {
            "id": "python3",
            "name": "Python 3",
            "extensions": []
        }