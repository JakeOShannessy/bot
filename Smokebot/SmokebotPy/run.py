#!/bin/python

import glob
from cases import get_cases, Case
import programs
import os
import shutil
import threading
import concurrent.futures
import itertools
import argparse

p = '.'


def create_case_dir_name(path):
    return os.path.basename(path) + '.d'


def stop_path(path):
    (fds_prefix, _) = os.path.splitext(os.path.basename(path))
    return os.path.join(os.path.dirname(path), fds_prefix+".stop")


class Suite:
    def __init__(self, cases: list[Case], dir="run_dir"):
        self.cases = cases
        # TODO: split this into a generic executor class that could use SLURM
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)
        self.dir = dir

    def run_case(self, case):
        """Run a given case"""
        # Create a new directory to run in
        caserundir = os.path.join(
            self.dir, create_case_dir_name(case.path))
        os.makedirs(caserundir, exist_ok=True)
        newinputpath = os.path.join(
            caserundir, os.path.basename(case.path))
        if os.path.isfile(stop_path(newinputpath)):
            print(stop_path(newinputpath), "exists, skipping")
            return
        # Copy input file to that dir
        shutil.copyfile(case.path, newinputpath)
        programs.run(case.program, caserundir, os.path.basename(case.path))
        # Create a stop file
        open(stop_path(newinputpath), 'w')

    def run(self):
        """Run all of the cases"""
        return concurrent.futures.wait(self.executor.map(self.run_case, self.cases))

    def snapshot_path(self):
        os.path.join(self.dir, "snapshot.zip")

    def create_snapshot(self):
        """Create a zipped snapshot of results"""
        shutil.make_archive(os.path.join(
            self.dir, "snapshot"), 'zip', self.dir)


class SmvProgramPath:
    def __init__(self, path):
        self.__path = path

    def get_path(self):
        return self.__path

    path = property(get_path)


class SmvProgramRepo:
    def __init__(self, path, url="https://github.com/firemodels/smv.git", branch=None):
        self.repo_url = url
        self.base_path = path
        self.branch = branch
        self.setup_complete = False

    def __repo_path(self):
        return os.path.join(self.base_path, "repo")

    def __build_path(self):
        return os.path.join(self.base_path, "build")

    def setup(self):
        programs.git_clone(self.repo_url, self.__repo_path(), self.branch)
        programs.setup_cmake(self.__repo_path(), self.__build_path())
        programs.run_cmake(self.__repo_path(), self.__build_path())

    def get_path(self):
        if not self.setup_complete:
            self.setup()
            self.setup_complete = True
        return os.path.join(self.__build_path(), "smokeview")

    path = property(get_path)


class ReferenceImagesZip:
    def __init__(self, path, url="https://github.com/firemodels/fig/archive/dfcabce0508b79a60d4ea6a9699cf8532cdd02c2.zip", branch=None):
        self.repo_url = url
        self.base_path = path
        self.branch = branch
        self.setup_complete = False

    def __repo_path(self):
        return os.path.join(self.base_path, "repo")

    def __build_path(self):
        return os.path.join(self.base_path, "build")

    def setup(self):
        programs.git_clone(self.repo_url, self.__repo_path(), self.branch)
        programs.setup_cmake(self.__repo_path(), self.__build_path())
        programs.run_cmake(self.__repo_path(), self.__build_path())

    def get_path(self):
        if not self.setup_complete:
            self.setup()
            self.setup_complete = True
        return os.path.join(self.__build_path(), "smokeview")

    path = property(get_path)

    def images_path(self):
        return glob.glob('./**/*.png', recursive=True,
                         root_dir=os.path.join(self.__base_path(), "./Manuals"))


class Comparison:
    def __init__(self, cases: list[Case], snapshot_path: str, base_smv=SmvProgramPath("smokeview"), current_smv=SmvProgramPath("smokeview"), dir="post_dir"):
        self.cases = cases
        self.root = "comparison"
        self.dir = dir
        self.snapshot_path = snapshot_path
        self.dirs = ["SMV_Summary", "SMV_User_Guide",
                     "SMV_Verification_Guide"]
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=8)
        if type(base_smv) is str:
            self.base_smv = SmvProgramPath(base_smv)
        else:
            self.base_smv = base_smv
        if type(current_smv) is str:
            self.current_smv = SmvProgramPath(current_smv)
        else:
            self.current_smv = current_smv

    def __base_path(self):
        return os.path.join(self.root, "base")

    def __current_path(self):
        return os.path.join(self.root, "current")

    def __comparison_path(self):
        return os.path.join(self.root, "comparison")

    def run_base(self):
        base_dir = self.__base_path()
        base_sims_dir = os.path.join(base_dir, "sims")
        os.makedirs(base_sims_dir, exist_ok=True)
        for dir in self.dirs:
            os.makedirs(os.path.join(base_dir, "Manuals", dir,
                        "SCRIPT_FIGURES"), exist_ok=True)
        shutil.unpack_archive(self.snapshot_path, base_sims_dir)
        self.run_scripts(base_sims_dir, self.base_smv)

    def run_current(self):
        current_dir = self.__current_path()
        current_sims_dir = os.path.join(current_dir, "sims")
        os.makedirs(current_sims_dir, exist_ok=True)
        for dir in self.dirs:
            os.makedirs(os.path.join(current_dir, "Manuals", dir,
                        "SCRIPT_FIGURES"), exist_ok=True)
        shutil.unpack_archive(self.snapshot_path, current_sims_dir)
        self.run_scripts(current_sims_dir, self.current_smv)

    def run(self):
        """Run the deafult script for all cases"""
        self.run_base()
        self.run_current()

    def run_script(self, dir, case, smv):
        """Run a particular script"""
        print("run", case.path, "with", smv, "in", dir)
        # TODO: this is a bit of hack
        ini_root = os.path.join(p, "Visualization")
        ini_files = glob.glob('./**/*.ini', recursive=True,
                              root_dir=ini_root)
        jpeg_files = glob.glob('./**/*.jpg', recursive=True,
                               root_dir=ini_root)
        png_files = glob.glob('./**/*.png', recursive=True,
                              root_dir=ini_root)
        case_rundir = os.path.join(
            dir, create_case_dir_name(case.path))
        source_script_path = case.script_path()
        (fds_prefix, _) = os.path.splitext(
            os.path.basename(case.path))
        # Copy script file to that dir
        if os.path.isfile(source_script_path):
            dest_script_path = os.path.join(
                case_rundir, case.script_name())
            shutil.copyfile(source_script_path, dest_script_path)
            for file in (ini_files+jpeg_files+png_files):
                src_path = os.path.join(ini_root, file)
                dest_path = os.path.join(
                    case_rundir, os.path.basename(file))
                shutil.copyfile(src_path, dest_path)
            if os.path.isfile(stop_path(dest_script_path)):
                os.remove(stop_path(dest_script_path))
            programs.run_smv_script(
                case_rundir, fds_prefix + ".smv", smv_path=smv.path)
            # open(stop_path(dest_script_path), 'w')

    def run_scripts(self, dir, smv):
        print("smv_path:", smv)
        return self.executor.map(self.run_script, itertools.repeat(dir), self.cases, itertools.repeat(smv))

    def compare_image(self, file):
        """Give a filename, compare the base and current"""
        diff = None
        current_file = os.path.join(self.__base_path(), "./Manuals", file)
        comparison_path = None
        if os.path.isfile(current_file):
            comparison_path = os.path.join(self.__comparison_path(), file)
            diff = programs.compare_images(os.path.join(self.__base_path(), "./Manuals", file),
                                           os.path.join(self.__current_path(), "./Manuals", file), comparison_path)
            print("diff", diff)
        diff = {
            "base": file,
            "current": current_file,
            "comparison": comparison_path,
            "diff": diff
        }
        return diff

    def compare_images(self):
        """Compare all images"""
        files = glob.glob('./**/*.png', recursive=True,
                          root_dir=os.path.join(self.__base_path(), "./Manuals"))
        comparison_dir = self.__comparison_path()
        os.makedirs(comparison_dir, exist_ok=True)
        for dir in self.dirs:
            os.makedirs(os.path.join(comparison_dir, "Manuals", dir,
                        "SCRIPT_FIGURES"), exist_ok=True)
        return self.executor.map(self.compare_image, files)


class SmokebotPy:
    def __init__(self, cases=[], force=False, dir="smokebot_temp_dir", base_smv="/home/jake/smv-master/.vscode/build/smokeview",
                 current_smv="/home/jake/smv/.vscode/build/smokeview"):
        self.cases = cases
        self.dir = dir
        self.base_smv = base_smv
        self.current_smv = current_smv
        self.force = force

    def add_cases(self, cases):
        if type(cases) is str:
            self.cases += get_cases(cases)
        else:
            self.cases += cases

    def run(self):
        main_suite = Suite(self.cases, dir=os.path.join(
            self.dir, "run_dir"))

        if self.force or not os.path.isfile(main_suite.snapshot_path()):
            main_suite.run()
            main_suite.create_snapshot()

        comparison = Comparison(self.cases, main_suite.snapshot_path(), base_smv=self.base_smv,
                                current_smv=self.case_smv, dir=os.path.join(self.dir, "post_dir"))

        os.environ["SMOKEVIEW_OBJECT_DEFS"] = "/home/jake/smv-master/Build/smokeview/gnu_linux_64/objects.svo"

        comparison.run()
        comparisons = comparison.compare_images()

        for diff in comparisons:
            print(diff["base"], diff["current"],
                  diff["comparison"], diff["diff"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog='SmokebotPy',
        description='A simple utility to run Smokebot outside of a cluster')
    parser.add_argument("-f", "--force", action="store_true",
                        help='force all steps to be re-run (default: false)')
    args = parser.parse_args()

    smoke_bot = SmokebotPy(force=args.force)
    smoke_bot.add_cases("../../../smv/Verification/scripts/cases.json")
    smoke_bot.base_smv = SmvProgramRepo(
        os.path.join(smoke_bot.dir, "builds/base"))
    smoke_bot.current_smv = SmvProgramRepo(
        os.path.join(smoke_bot.dir, "builds/current"), url="https://github.com/JakeOShannessy/smv.git", branch="read-object-no-global")

    print(smoke_bot.base_smv.path)
    print(smoke_bot.current_smv.path)
    # smoke_bot.run()
