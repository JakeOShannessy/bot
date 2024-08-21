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
import json

p = '~/smv/Verification'

default_root_path = "smokebot_temp_dir"


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
    def __init__(self, root_path=default_root_path, url="https://github.com/firemodels/smv.git", branch=None):
        self.repo_url = url
        self.branch = branch
        self.hash = programs.git_get_hash(self.repo_url, self.branch)
        self.base_path = os.path.join(root_path, "run", self.hash)
        self.setup_complete = False
        self.release = False
        self.force = False

    def __repo_path(self):
        return os.path.join(self.base_path, "repo")

    def __build_path(self):
        return os.path.join(self.base_path, "build")

    def __install_path(self):
        install_path = "dist-debug"
        if self.release:
            install_path = "dist"
        return os.path.join(self.base_path, install_path)

    def __exec_name(self):
        if platform.system() == "Windows":
            return "smokeview.exe"
        else:
            return "smokeview"

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
        programs.install_cmake(self.__build_path(),
                               self.__install_path(), release=self.release)

    def get_path(self):
        bin_path = None
        if self.release:
            bin_path = os.path.join(
                self.__install_path(), "bin", self.__exec_name())
        else:
            bin_path = os.path.join(
                self.__install_path(), "bin", self.__exec_name())
        if not os.path.exists(bin_path):
            print(bin_path, "does not exist")
            if not self.setup_complete:
                self.setup()
                self.setup_complete = True
                return self.get_path()
            else:
                raise "setup failed"
        return bin_path

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
    def __init__(self, cases: list[Case] = [], src="smokeview", dir="image_source"):
        self.dir = dir
        # if not src:
        #     self.src = SmvProgramRepo(os.path.join(self.dir, "run"))
        # else:
        self.src = src
        self.cases = cases
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
        self.dirs = ["SMV_Summary", "SMV_User_Guide",
                     "SMV_Verification_Guide"]
        self.override_snapshot = None
        self.setup_complete = False

    def __snapshot_path(self):
        if self.override_snapshot:
            return self.override_snapshot
        return os.path.join(self.dir, "snapshot.zip")

    def __sims_dir(self):
        return os.path.join(self.dir, "sims")

    def __images_dir(self):
        return os.path.join(self.dir)

    def setup(self):
        self.src.setup()
        self.setup_complete = True

    def run(self):
        base_sims_dir = self.__sims_dir()
        base_images_dir = self.__images_dir()
        os.makedirs(base_sims_dir, exist_ok=True)
        for dir in self.dirs:
            os.makedirs(os.path.join(base_images_dir, "Manuals", dir,
                        "SCRIPT_FIGURES"), exist_ok=True)
        # TODO: check that snapshot exists
        if len(os.listdir(base_sims_dir)) == 0:
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
            smv_name = fds_prefix + ".smv"
            result = programs.run_smv_script(
                case_rundir, smv_name, smv_path=smv, objpath=os.path.abspath(os.path.join(smv, "../../../repo/Build/for_bundle/objects.svo")))
            if result.returncode == 0:
                print(f"completed: {smv_name}",
                      f"{bcolors.OKGREEN}OK{bcolors.ENDC}", sep="\t")
            else:
                print(f"completed: {smv_name}",
                      f"{bcolors.FAIL}FAILED{bcolors.ENDC}", sep="\t")
            with open(os.path.join(case_rundir, fds_prefix + ".stdout"), 'w') as f:
                f.write(result.stdout)
            with open(os.path.join(case_rundir, fds_prefix + ".stderr"), 'w') as f:
                f.write(result.stderr)
            return (case.script_name(), result)

    def run_scripts(self, dir, src):
        sentinel_path = os.path.join(self.dir, "scripts_complete")
        if os.path.exists(sentinel_path):
            return
        else:
            res = list(self.executor.map(self.run_script, itertools.repeat(
                dir), self.cases, itertools.repeat(src)))
            open(sentinel_path, 'w')
            return

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
    def __init__(self, images_a, images_b, dir="post_dir"):
        self.root = dir
        self.images_a = images_a
        self.images_b = images_b
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=8)
        self.dirs = ["SMV_Summary", "SMV_User_Guide",
                     "SMV_Verification_Guide"]

    def __base_path(self):
        return os.path.join(self.root, "base")

    def __current_path(self):
        return os.path.join(self.root, "current")

    def __comparison_path(self):
        return os.path.join(self.root, "comparison")

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
        comparison_dir = self.__comparison_path()
        os.makedirs(comparison_dir, exist_ok=True)
        return list(self.executor.map(self.compare_image, self.images_a, itertools.repeat(self.images_b)))


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
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=8)

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


def print_results(results):
    """
    Prints the result of running smokeview scripts with colored output.
    """
    for (scriptname, result) in results:
        if result.returncode == 0:
            print(scriptname, f"{bcolors.OKGREEN}OK{bcolors.ENDC}", sep="\t")
        else:
            print(scriptname, f"{bcolors.FAIL}FAILED{bcolors.ENDC}", sep="\t")


def run_images(repo_url: str, branch: str, snapshot_path: str, cases):
    """
    Run images for a repo/branch
    """
    sm_a = SmvProgramRepo(
        url=repo_url, branch=branch)
    ri = RunImages(cases,
                   src=sm_a.path, dir=sm_a.base_path)
    ri.override_snapshot = snapshot_path
    ri.run()
    return {"image_paths": ri.image_paths(), "hash": sm_a.hash, "url": sm_a.repo_url, "branch": sm_a.branch}


def print_comparison_results(comparison_results):
    rmse_tolerance = 0.1
    # comparisons within tolerance
    ok_comparisons = []
    bad_comparisons = []
    for diff in comparison_results:
        diff_val = diff["diff"]
        if not diff["comparison"]:
            bad_comparisons.append(
                (os.path.basename(diff["base"]), None, None))
            continue
        image_name = os.path.basename(diff["comparison"])
        if diff_val != None and diff_val < rmse_tolerance:
            ok_comparisons.append((image_name, diff_val, diff["comparison"]))
        else:
            bad_comparisons.append((image_name, diff_val, diff["comparison"]))
    print(
        f"  {bcolors.OKGREEN}{len(ok_comparisons)} comparisons OK{bcolors.ENDC}", sep="\t")
    # bad_comparisons.sort(key=lambda x: x[1])
    for (image_name, diff_val, image_path) in bad_comparisons:
        if diff_val == None:
            print(f"  {image_name}",
                  f"{bcolors.FAIL}NO CURRENT IMAGE{bcolors.ENDC}", sep="\t")
        else:
            print(f"  {image_name}",
                  f"{bcolors.FAIL}{diff_val}{bcolors.ENDC}: {image_path}", sep="\t")
    if len(bad_comparisons) > 0:
        print(
            f"  {bcolors.FAIL}{len(bad_comparisons)} comparisons NOT OK{bcolors.ENDC}", sep="\t")
    else:
        print(
            f"  {bcolors.OKGREEN}{len(bad_comparisons)} comparisons NOT OK{bcolors.ENDC}", sep="\t")


def print_comparison_results_full(comparison_results):
    rmse_tolerance = 0.1
    for diff in comparison_results:
        diff_val = diff["diff"]
        if not diff["comparison"]:
            continue
        image_name = os.path.basename(diff["comparison"])
        if diff_val != None and diff_val < rmse_tolerance:
            print("  ", image_name,
                  f"{bcolors.OKGREEN}{diff_val}{bcolors.ENDC}", sep="\t")
        else:
            print("  ", image_name,
                  f"{bcolors.FAIL}{diff_val}{bcolors.ENDC}", sep="\t")


class ManyComparison:
    def __init__(self, base_url, base_branch, cases=[], force=False, dir="smokebot_temp_dir", base_image_source=None,
                 current_image_source=None, snapshot_path="./snapshot.zip"):
        self.cases = cases
        self.snapshot_path = snapshot_path
        self.base_url = base_url
        self.base_branch = base_branch
        self.comparison_sources = []

    def add_repo_branch(self, repo_url, branch):
        self.comparison_sources.append({
            "url": repo_url,
            "branch": branch,
        })

    def add_repo_branches(self, repo_url, branches):
        for branch in branches:
            self.add_repo_branch(repo_url, branch)

    def run(self):
        images_base = run_images(self.base_url,
                                 self.base_branch, self.snapshot_path, self.cases)
        images_others = []
        # TODO: do these in concurrently
        for repo in self.comparison_sources:
            try:
                images_b = run_images(repo["url"],
                                      repo["branch"], self.snapshot_path, self.cases)
                images_others.append(images_b)
            except:
                images_others.append(
                    {"error": True, "url": repo["url"], "branch": repo["branch"]})

        full_results = {
            "base_hash": images_base["hash"],
            "comparisons": []
        }
        for other in images_others:
            if "error" in other and other["error"]:
                full_results["comparisons"].append(
                    {"error": other["error"],  "url": other["url"], "branch": other["branch"]})
            else:
                compare_dir = f"{images_base["hash"]}-{other["hash"]}"
                results_summary_path = os.path.join(
                    default_root_path, "compare", compare_dir, "results.json")
                comparison_results = None
                if os.path.exists(results_summary_path):
                    with open(results_summary_path) as f:
                        d = json.load(f)
                        comparison_results = d
                else:
                    comparison = Comparison(
                        images_base["image_paths"], other["image_paths"], dir=os.path.join(default_root_path, "compare", compare_dir, "images"))
                    comparison_results = comparison.compare_images()
                full_results["comparisons"].append(
                    {"hash": other["hash"], "results": comparison_results, "url": other["url"], "branch": other["branch"]})
                with open(results_summary_path, "w") as fp:
                    json.dump(comparison_results, fp, indent=2)
        with open(os.path.join(default_root_path, "full_results.json"), "w") as fp:
            json.dump(full_results, fp, indent=2)
        return full_results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog='SmokebotPy',
        description='A simple utility to run Smokebot outside of a cluster')
    parser.add_argument("-f", "--force", action="store_true",
                        help='force all steps to be re-run (default: false)')
    args = parser.parse_args()

    smoke_bot = SmokebotPy(force=args.force)

    runner = ManyComparison("https://github.com/firemodels/smv.git",
                            "master",
                            get_cases("./cases.json"))
    runner.add_repo_branches(
        "https://github.com/JakeOShannessy/smv.git", [
            "read-smv-no-global",
            "read-tour-no-global",
            "read-hvac-no-global",
            "meshes-no-global",
            "read-colorbar-no-global",
            "read-smoke-no-global",
            "read-slice-no-global",
            "read-label-no-global",
            "read-part-no-global",
        ])
    results = runner.run()
    print("base hash:", results["base_hash"])
    for comparison in results["comparisons"]:
        print(f"{bcolors.OKCYAN}{comparison["url"]} {comparison["branch"]} {comparison["hash"] if "hash" in comparison else ""}:{bcolors.ENDC}")
        if "error" in comparison and comparison["error"]:
            print(f"  {bcolors.FAIL}BUILD FAILED{bcolors.ENDC}")
        else:
            print_comparison_results(comparison["results"])
