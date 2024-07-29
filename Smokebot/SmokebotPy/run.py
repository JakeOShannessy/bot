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
import urllib.request
import platform

p = '~/smv/Verification'


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


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
        os.makedirs(self.dir, exist_ok=True)

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

    def snapshot_path(self) -> str:
        return os.path.join(self.dir, "snapshot.zip")

    def create_snapshot(self):
        """Create a zipped snapshot of results"""
        p = os.path.join(
            self.dir, "snapshot")
        print("saving zip to", p)
        shutil.make_archive(p, 'zip', self.dir)


class SmvProgramPath:
    def __init__(self, path):
        self.__path = path

    def get_path(self):
        return self.__path

    path = property(get_path)


class SmvProgramRepo:
    def __init__(self, path, url="https://github.com/firemodels/smv.git", branch=None, snapshot_path="snapshot.zip"):
        self.repo_url = url
        self.base_path = path
        self.branch = branch
        self.setup_complete = False
        self.release = False
        self.force = False
        self.snapshot_path = snapshot_path

    def __repo_path(self):
        return os.path.join(self.base_path, "repo")

    def __build_path(self):
        return os.path.join(self.base_path, "build")

    def __object_path(self):
        return os.path.join(self.__build_path(), "objects.svo")

    objpath = property(__object_path)

    def __run_path(self):
        return os.path.join(self.base_path, "run_dir")

    def setup(self):
        programs.git_clone(self.repo_url, self.__repo_path(), self.branch)
        programs.setup_cmake(self.__repo_path(),
                             self.__build_path(), release=self.release)
        programs.run_cmake(self.__repo_path(), self.__build_path())

    def get_path(self):
        if not self.setup_complete:
            self.setup()
            self.setup_complete = True
        if platform.system() == "Windows":
            if self.release:
                return os.path.join(self.__build_path(), "Release", "smokeview")
            else:
                return os.path.join(self.__build_path(), "Debug", "smokeview")
        else:
            return os.path.join(self.__build_path(), "smokeview")

    path = property(get_path)


class ReferenceImagesZip:
    def __init__(self, url="https://github.com/firemodels/fig/archive/dfcabce0508b79a60d4ea6a9699cf8532cdd02c2.zip", sub_dir="fig-dfcabce0508b79a60d4ea6a9699cf8532cdd02c2/smv/Reference_Figures/Default", dir="image_source"):
        self.dir = dir
        self.sub_dir = sub_dir
        self.url = url

    def __unpacked_dir(self):
        return os.path.join(self.dir, "unpacked")

    def __images_dir(self):
        return os.path.join(self.dir, "images")

    def __zip_path(self):
        return os.path.join(self.dir, "images.zip")

    def run(self):
        os.makedirs(self.dir, exist_ok=True)
        (path, message) = urllib.request.urlretrieve(self.url, self.__zip_path())
        os.makedirs(self.__images_dir(), exist_ok=True)
        os.makedirs(self.__unpacked_dir(), exist_ok=True)
        shutil.unpack_archive(path, self.__unpacked_dir())
        shutil.rmtree(self.__images_dir())
        shutil.copytree(os.path.join(self.__unpacked_dir(),
                        self.sub_dir), self.__images_dir())

    def image_paths(self):
        paths = glob.glob('./**/*.png', recursive=True,
                          root_dir=self.__images_dir())
        added_paths = []
        for path in paths:
            added_paths.append(os.path.join(self.__images_dir(), path))
        return added_paths


class RunImages:
    def __init__(self, cases: list[Case] = [], src=None, dir="image_source"):
        self.dir = dir
        if not src:
            self.src = SmvProgramRepo(os.path.join(self.dir, "run"))
        else:
            self.src = src
        self.cases = cases
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.dirs = ["SMV_Summary", "SMV_User_Guide",
                     "SMV_Verification_Guide"]
        self.override_snapshot = None

    def __snapshot_path(self):
        if self.override_snapshot:
            return self.override_snapshot
        return os.path.join(self.dir, "snapshot.zip")

    def __sims_dir(self):
        return os.path.join(self.dir, "sims")

    def __images_dir(self):
        return os.path.join(self.dir)

    def run(self):
        self.src.setup()
        base_sims_dir = self.__sims_dir()
        base_images_dir = self.__images_dir()
        os.makedirs(base_sims_dir, exist_ok=True)
        for dir in self.dirs:
            os.makedirs(os.path.join(base_images_dir, "Manuals", dir,
                        "SCRIPT_FIGURES"), exist_ok=True)
        # TODO: check that snapshot exists
        print("unpacking", self.__snapshot_path(), base_sims_dir)
        shutil.unpack_archive(self.__snapshot_path(), base_sims_dir)
        return self.run_scripts(base_sims_dir, self.src)

    def run_script(self, dir: str, case: Case, smv):
        """Run a particular script"""
        # TODO: this is a bit of hack
        ini_root = os.path.dirname(case.script_path())
        ini_files = glob.glob('./**/*.ini', recursive=True,
                              root_dir=ini_root)
        jpeg_files = glob.glob('./**/*.jpg', recursive=True,
                               root_dir=ini_root)
        png_files = glob.glob('./**/*.png', recursive=True,
                              root_dir=ini_root)
        case_rundir = os.path.join(
            dir, create_case_dir_name(case.path))
        (fds_prefix, _) = os.path.splitext(
            os.path.basename(case.path))
        # Copy script file to that dir
        if os.path.isfile(case.script_path()):
            dest_script_path = os.path.join(
                case_rundir, case.script_name())
            shutil.copyfile(case.script_path(), dest_script_path)
            for file in (ini_files+jpeg_files+png_files):
                src_path = os.path.join(ini_root, file)
                dest_path = os.path.join(
                    case_rundir, os.path.basename(file))
                shutil.copyfile(src_path, dest_path)
            if os.path.isfile(stop_path(dest_script_path)):
                os.remove(stop_path(dest_script_path))
            result = programs.run_smv_script(
                case_rundir, fds_prefix + ".smv", smv_path=smv.path, objpath=smv.objpath)
            with open(os.path.join(case_rundir, fds_prefix + ".stdout"), 'w') as f:
                f.write(result.stdout)
            with open(os.path.join(case_rundir, fds_prefix + ".stderr"), 'w') as f:
                f.write(result.stderr)
            return (case.script_name(), result)

    def run_scripts(self, dir, src):
        return list(self.executor.map(self.run_script, itertools.repeat(dir), self.cases, itertools.repeat(src)))

    def image_paths(self):
        paths = glob.glob('./**/*.png', recursive=True,
                          root_dir=self.__images_dir())
        added_paths = []
        for path in paths:
            added_paths.append(os.path.join(self.__images_dir(), path))
        return added_paths

    def add_cases(self, cases):
        if type(cases) is str:
            self.cases += get_cases(cases)
        else:
            self.cases += cases


class Comparison:
    def __init__(self, image_source_a, image_source_b, dir="post_dir"):
        self.root = dir
        self.image_source_a = image_source_a
        self.image_source_b = image_source_b
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=8)
        self.dirs = ["SMV_Summary", "SMV_User_Guide",
                     "SMV_Verification_Guide"]

    def __base_path(self):
        return os.path.join(self.root, "base")

    def __current_path(self):
        return os.path.join(self.root, "current")

    def __comparison_path(self):
        return os.path.join(self.root, "comparison")

    def run_base(self):
        return self.image_source_a.run()

    def run_current(self):
        return self.image_source_b.run()

    def run(self):
        """Run the deafult script for all cases"""
        base_results = self.run_base()
        current_results = self.run_current()
        return {
            "base": base_results,
            "current": current_results,
        }

    def compare_image(self, file, files_b):
        """Give a filename, compare the base and current"""
        diff = None
        current_file = None
        for file_b in files_b:
            if os.path.basename(file) == os.path.basename(file_b):
                current_file = file_b
                break
        comparison_path = None
        if not current_file:
            print("no current_file for", os.path.basename(file))
        if current_file and os.path.isfile(current_file):
            comparison_path = os.path.join(
                self.__comparison_path(), os.path.basename(file))
            print("comparing", os.path.basename(file))
            diff = programs.compare_images(
                file,  current_file, comparison_path)
        diff = {
            "base": file,
            "current": current_file,
            "comparison": comparison_path,
            "diff": diff
        }
        return diff

    def compare_images(self):
        """Compare all images"""
        files_a = self.image_source_a.image_paths()
        files_b = self.image_source_b.image_paths()
        comparison_dir = self.__comparison_path()
        os.makedirs(comparison_dir, exist_ok=True)
        return list(self.executor.map(self.compare_image, files_a, itertools.repeat(files_b)))


class SmokebotPy:
    def __init__(self, cases=[], force=False, dir="smokebot_temp_dir", base_image_source=None,
                 current_image_source=None):
        self.cases = cases
        self.dir = dir
        self.force = force
        if not base_image_source:
            # The default base image source is a reference set hosted online
            self.base_image_source = ReferenceImagesZip()

        if not current_image_source:
            # The default current image source is to clone and build from git
            self.current_image_source = RunImages()

        self.__base_image_source.dir = os.path.join(self.dir, "images_a")
        self.__current_image_source.dir = os.path.join(self.dir, "images_b")

    def get_base_image_source(self):
        return self.__base_image_source

    def get_current_image_source(self):
        return self.__current_image_source

    def set_base_image_source(self, src):
        self.__base_image_source = src
        self.__base_image_source.dir = os.path.join(self.dir, "images_a")

    def set_current_image_source(self, src):
        self.__current_image_source = src
        self.__current_image_source.dir = os.path.join(self.dir, "images_b")

    base_image_source = property(get_base_image_source, set_base_image_source)
    current_image_source = property(
        get_current_image_source, set_current_image_source)

    def run(self):
        main_suite = Suite(self.cases, dir=os.path.join(
            self.dir, "run_dir"))
        if self.force or not os.path.isfile(main_suite.snapshot_path()):
            main_suite.run()
            main_suite.create_snapshot()
        comparison = Comparison(
            self.base_image_source, self.current_image_source, dir=os.path.join(self.dir, "post_dir"))

        run_results = comparison.run()
        comparisons = comparison.compare_images()

        if run_results["base"]:
            print_results(run_results["base"])
        if run_results["current"]:
            print_results(run_results["current"])
        rmse_tolerance = 0.1
        for diff in comparisons:
            diff_val = diff["diff"]
            if not diff["comparison"]:
                continue
            image_name = os.path.basename(diff["comparison"])
            if diff_val != None and diff_val < rmse_tolerance:
                print(image_name,
                      f"{bcolors.OKGREEN}{diff_val}{bcolors.ENDC}", sep="\t")
            else:
                print(image_name,
                      f"{bcolors.FAIL}{diff_val}{bcolors.ENDC}", sep="\t")


def print_results(results):
    """
    Prints the result of running smokeview scripts with colored output.
    """
    for (scriptname, result) in results:
        if result.returncode == 0:
            print(scriptname, f"{bcolors.OKGREEN}OK{bcolors.ENDC}", sep="\t")
        else:
            print(scriptname, f"{bcolors.FAIL}FAILED{bcolors.ENDC}", sep="\t")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog='SmokebotPy',
        description='A simple utility to run Smokebot outside of a cluster')
    parser.add_argument("-f", "--force", action="store_true",
                        help='force all steps to be re-run (default: false)')
    args = parser.parse_args()

    smoke_bot = SmokebotPy(force=args.force)

    # # Run images by building from source, the default is the NIST HEAD
    # smoke_bot.base_image_source = RunImages()
    # smoke_bot.base_image_source.add_cases(
    #     "../../../smv/Verification/scripts/cases.json")

    # Run images by building from source from a particular branch
    smoke_bot.current_image_source = RunImages(
        dir=smoke_bot.current_image_source.dir)
    # smoke_bot.current_image_source.src.repo_url = "https://github.com/JakeOShannessy/smv.git"
    # smoke_bot.current_image_source.src.branch = "read-smoke-no-global"
    smoke_bot.current_image_source.add_cases(
        "../../../smv/Verification/scripts/cases.json")
    smoke_bot.current_image_source.override_snapshot = "./snapshot.zip"

    smoke_bot.run()
