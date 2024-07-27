#!/bin/python
import json
import os


class Case:
    def __init__(self, program, path, processes=None, threads=None):
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


class FdsCase(Case):
    def __init__(self, path, processes=None, threads=None):
        Case.__init__(self, 'fds', path, processes=processes, threads=threads)


class CFastCase(Case):
    def __init__(self, path, processes=None, threads=None):
        Case.__init__(self, 'cfast', path,
                      processes=processes, threads=threads)


def get_cases(cases_path: str):
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
            print("path:", path)
            if l["program"] == "fds":
                cases.append(
                    FdsCase(path, processes=l.get("n_processes"), threads=l.get("n_threads")))
            elif l["program"] == "cfast":
                cases.append(
                    CFastCase(path, processes=l.get("n_processes"), threads=l.get("n_threads")))
    return cases
