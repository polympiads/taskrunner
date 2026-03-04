
import os
from typing import TYPE_CHECKING
import tree_sitter_java as tsjava
from tree_sitter import Language, Node, Parser, Query, QueryCursor

from django.conf import settings
if TYPE_CHECKING:
    from ccs.feed.languages import LanguagesCCSJson

from judge.languages.base import CompiledLanguage
from sandbox.isolate import Isolate

class JavaLanguage (CompiledLanguage):
    def language_name(self):
        return "Java"
        
    def find_main_class (self, content: bytes):
        JAVA_LANGUAGE = Language(tsjava.language())
        JAVA_PARSER   = Parser(JAVA_LANGUAGE)

        tree = JAVA_PARSER.parse(content)

        query = Query(JAVA_LANGUAGE, """
            (class_declaration
                name: (identifier) @class_name
                body: (class_body
                    (method_declaration
                        (modifiers ["public"] ["static"])
                        type: (void_type)
                        name: (identifier) @method_name
                        parameters: (formal_parameters)
                        (#eq? @method_name "main")
                    )
                )
            )
        """)

        cursor = QueryCursor(query)
        captures = cursor.captures(tree.root_node)
        class_names = captures.get('class_name', [])
        def node_to_string (node: Node):
            return content[node.start_byte:node.end_byte].decode()
        class_names = list(map(node_to_string, class_names))

        if len(class_names) == 0:
            raise JavaLanguage.FileFormatError("Could not find class with public static void main.")
        if len(class_names) > 1:
            raise JavaLanguage.FileFormatError(
                f"Multiple classes with public static void main: {', '.join(class_names)}")
        return class_names[0]
    def find_public_class (self, content: bytes):
        JAVA_LANGUAGE = Language(tsjava.language())
        JAVA_PARSER   = Parser(JAVA_LANGUAGE)

        tree = JAVA_PARSER.parse(content)

        query = Query(JAVA_LANGUAGE, """
            (class_declaration
                (modifiers "public")
                name: (identifier) @class_name)
        """)

        cursor = QueryCursor(query)
        captures = cursor.captures(tree.root_node)
        class_names = captures.get('class_name', [])
        def node_to_string (node: Node):
            return content[node.start_byte:node.end_byte].decode()
        class_names = list(map(node_to_string, class_names))

        if len(class_names) == 0:
            return None
        if len(class_names) > 1:
            raise JavaLanguage.FileFormatError(
                f"Multiple public classes: {', '.join(class_names)}")
        return class_names[0]

    def enable_simple_memory (self) -> bool:
        return False
    def number_execution_processes(self):
        return Isolate.MAX_NUMBER_PROCESS
    def get_executable_name(self, filename):
        return os.path.splitext(filename)[0] + ".jar"
    def get_source_code_filename(self, file):
        with open(file, "rb") as fr:
            entry = self.find_public_class(fr.read())
            if entry is None:
                return super().get_source_code_filename(file)
            else:
                return f"{entry}.java"
    def get_compilation_commands(self, fileexe, filename, file: str):
        with open(file, "rb") as file:
            content    = file.read()
            main_class = self.find_main_class(content)

            return [
                [ settings.JAVA_COMPILER, filename ],
                [ "/bin/bash", "-c", f"{settings.JAR_COMPILER} cfe {fileexe} {main_class} *.class"]
            ]
    def get_execution_command (self, filename: str):
        return [ settings.JAVA_EXECUTABLE, "-jar", filename ]
    def extra_execution_directories(self):
        return settings.JVM_DIRECTORIES
    def extra_compilation_directories(self):
        return settings.JVM_DIRECTORIES
    
    @property
    def ccs_language_information (self) -> "LanguagesCCSJson":
        return {
            "id": "java",
            "name": "Java",
            "extensions": []
        }