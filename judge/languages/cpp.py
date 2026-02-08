
import os
import tempfile
import shutil

from typing import List

import aiofiles
import aiofiles.os

from config import CXX_COMPILER
from judge.languages.base import CompiledLanguage
from judge.languages.error import CompilationError
from sandbox.context import sandbox_open

class CppLanguage (CompiledLanguage):
    def __init__(self, cxx_version: str, cxx: str, cxx_flags: List[str]):
        super().__init__()

        self.cxx_version  = cxx_version
        self.cxx_compiler = [ cxx ] + cxx_flags
    
    def language_name(self):
        return f"C++{self.cxx_version}"

    def get_executable_name(self, filename):
        return os.path.splitext(filename)[0]
    def get_compilation_command(self, fileexe, filename):
        return self.cxx_compiler + [ "-o", fileexe, filename ]
        
    def get_execution_command (self, filename: str):
        return [filename]

GNU_GPP_23 = CppLanguage(
    "23", CXX_COMPILER, [
        "-Wall", "-Wextra", "-Wconversion", "-static", 
        "-DONLINE_JUDGE", "-O2", "-std=c++23"
    ]
)
