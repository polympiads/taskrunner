
import enum

from judge.languages.base import Language
from judge.languages.cpp import GNU_GPP_23
from judge.languages.python import PythonLanguage


class LanguageKind (enum.Enum):
    PYTHON = 0,
    CPP_23 = 1

def get_language (kind: LanguageKind) -> Language:
    match kind:
        case LanguageKind.PYTHON: return PythonLanguage()
        case LanguageKind.CPP_23: return GNU_GPP_23

    raise NotImplementedError(f"Could not recognize language kind {kind}")
def get_language_name (kind: LanguageKind) -> str:
    return get_language(kind).language_name()
