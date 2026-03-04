
from django_enumfield import enum

from judge.languages.base import Language
from judge.languages.cpp import GNU_GPP_23
from judge.languages.java import JavaLanguage
from judge.languages.python import PythonLanguage


class LanguageKind (enum.Enum):
    PYTHON = 0,
    CPP_23 = 1
    JAVA   = 2

def get_language_kind_from_extension (ext: str) -> LanguageKind:
    match ext:
        case ".py" | ".py3" | ".pypy3" | ".pypy3-64":
            return LanguageKind.PYTHON
        case ".cpp" | ".c":
            return LanguageKind.CPP_23
        case ".java":
            return LanguageKind.JAVA
    
    raise NotImplementedError(f"Could not recognize extension '{ext}'")
def get_language (kind: LanguageKind) -> Language:
    match kind:
        case LanguageKind.PYTHON: return PythonLanguage()
        case LanguageKind.CPP_23: return GNU_GPP_23
        case LanguageKind.JAVA  : return JavaLanguage()

    raise NotImplementedError(f"Could not recognize language kind {kind}")
def get_language_name (kind: LanguageKind) -> str:
    return get_language(kind).language_name()
