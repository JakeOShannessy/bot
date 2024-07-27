import json
import os

class Case:
    def __init__(self, program: str, path: str, processes=None, threads=None):
        self.program = program
        self.path = path
        self.processes = processes
        self.threads = threads

    def __ext_path(self, ext: str) -> str:
        (base_path, _) = os.path.splitext(self.path)
        return base_path + ext

    def script_path(self) -> str:
        return self.__ext_path(".ssf")

    def script_name(self) -> str:
        return os.path.basename(self.script_path())

    def ini_path(self) -> str:
        return self.__ext_path(".ini")


def get_cases(cases_path: str) -> list[Case]:
    """Get cases from a JSON file"""
    cases = []
    with open(cases_path) as f:
        d = json.load(f)
        for l in d:
            path = l["input_path"]
            if not os.path.isabs(path):
                # If the input path is not absolute, resolve it relative to
                # cases_path
                path = os.path.join(os.path.dirname(cases_path), path)
            cases.append(
                Case(l["program"], path, processes=l.get("n_processes"), threads=l.get("n_threads")))
    return cases
