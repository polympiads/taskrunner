
from typing import Dict, List, Tuple
import xml.etree.ElementTree as ET

class PolygonProblem:
    tests     : List[Tuple[str, str]]
    timelimit : float
    memlimit  : int
    checker   : str
    name      : str
    statement : str

    def __init__ (self):
        self.tests   = []
        self.checker = None

def read_polygon_problem (path: str):
    tree = ET.parse(path)
    root = tree.getroot()

    # This is a partial polygon problem reader
    # Maybe one day we could parse the full file

    number_tests   = 0
    input_pattern  = None
    answer_pattern = None
    checker_path   = None
    
    problem = PolygonProblem()
    def explore (x: "ET.Element[str]"):
        nonlocal number_tests, input_pattern, answer_pattern, checker_path
        if x.tag != "checker" and x.tag != "validators" \
            and x.tag != "solutions" and x.tag != "validators":
            for y in x:
                explore(y)

        if x.tag == "name":
            problem.name = x.attrib["value"]
        if x.tag == "test": number_tests += 1
        if x.tag == "input-path-pattern": input_pattern = x.text
        if x.tag == "answer-path-pattern": answer_pattern = x.text
        if x.tag == "statement" and x.attrib["language"] == "english" and x.attrib["type"] == "application/pdf":
            problem.statement = x.attrib["path"]
        if x.tag == "checker":
            for y in x:
                if y.tag == "source":
                    checker_path = y.attrib["path"]
        if x.tag == "time-limit":
            # the timelimit is in milliseconds, so convert to seconds
            problem.timelimit = int(x.text) / 1000
        if x.tag == "memory-limit":
            # memory limit in package is in bytes
            # memory limit for isolate is in kbytes
            problem.memlimit = int(x.text) // 1024

    explore(root)
    
    for test_id in range(1, number_tests + 1):
        problem.tests.append((
            input_pattern % test_id,
            answer_pattern % test_id
        ))
    problem.checker = checker_path
    
    return problem
