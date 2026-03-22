
import unittest

from judge.languages import LanguageKind, get_language, get_language_name
from judge.languages.cpp import GNU_GPP_23
from judge.languages.python import PythonLanguage


class TestLanguageKind(unittest.TestCase):
    def test_none_kind (self):
        with self.assertRaises(NotImplementedError):
            get_language(None)
    def test_default_kinds (self):
        assert type( get_language(LanguageKind.PYTHON) ) == PythonLanguage
        assert get_language(LanguageKind.CPP_23) is GNU_GPP_23
    def test_default_names (self):
        assert get_language_name(LanguageKind.PYTHON) == "Python"
        assert get_language_name(LanguageKind.CPP_23) == "C++23"
    def test_extensions (self):
        assert get_language(LanguageKind.CPP_23).extension == ".cpp"
        assert get_language(LanguageKind.JAVA).extension == ".java"
        assert get_language(LanguageKind.PYTHON).extension == ".py"