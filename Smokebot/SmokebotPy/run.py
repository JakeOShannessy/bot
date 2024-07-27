#!/bin/python

import glob
import cases
import programs
import os
import shutil
import threading
import concurrent.futures
import itertools

# The directory in which to run everything
rundir = 'temprundir'
p = '.'


def create_case_dir_name(path):
    return os.path.basename(path) + '.d'


def stop_path(path):
    (fds_prefix, _) = os.path.splitext(os.path.basename(path))
    return os.path.join(os.path.dirname(path), fds_prefix+".stop")


class Suite:
    def __init__(self, cases: list[cases.Case]):
        self.cases = cases
        # TODO: split this into a generic executor class that could use SLURM
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)
        self.rundir = rundir

    def run_case(self, case):
        """Run a given case"""
        # Create a new directory to run in
        caserundir = os.path.join(
            self.rundir, create_case_dir_name(case.path))
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

    def create_snapshot(self):
        """Create a zipped snapshot of results"""
        shutil.make_archive(os.path.join(self.rundir, "snapshot"), 'zip', self.rundir)


class Comparison:
    def __init__(self, cases: list[cases.Case]):
        self.cases = cases
        self.root = "comparison"
        self.rundir = rundir
        self.zip_path = os.path.join(self.rundir, "snapshot.zip")
        self.dirs = ["SMV_Summary", "SMV_User_Guide",
                     "SMV_Verification_Guide"]
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=8)

    def __base_path(self):
        return os.path.join(self.root, "base")

    def __current_path(self):
        return os.path.join(self.root, "current")

    def __comparison_path(self):
        return os.path.join(self.root, "comparison")

    def run_base(self, base_smv_path="smokeview"):
        base_dir = self.__base_path()
        base_sims_dir = os.path.join(base_dir, "sims")
        os.makedirs(base_sims_dir, exist_ok=True)
        for dir in self.dirs:
            os.makedirs(os.path.join(base_dir, "Manuals", dir,
                        "SCRIPT_FIGURES"), exist_ok=True)
        shutil.unpack_archive(self.zip_path, base_sims_dir)
        self.run_scripts(base_sims_dir, base_smv_path)

    def run_current(self,  current_smv_path="smokeview"):
        current_dir = self.__current_path()
        current_sims_dir = os.path.join(current_dir, "sims")
        os.makedirs(current_sims_dir, exist_ok=True)
        for dir in self.dirs:
            os.makedirs(os.path.join(current_dir, "Manuals", dir,
                        "SCRIPT_FIGURES"), exist_ok=True)
        shutil.unpack_archive(self.zip_path, current_sims_dir)
        self.run_scripts(current_sims_dir, current_smv_path)

    def run(self, base_smv_path, current_smv_path):
        """Run the deafult script for all cases"""
        # self.run_base(base_smv_path="smokeview")
        base_task = threading.Thread(target=self.run_base,   kwargs={
            "base_smv_path": base_smv_path})
        base_task.start()
        base_task.join()
        #   self.run_current(current_smv_path="smokeview")
        current_task = threading.Thread(target=self.run_current,   kwargs={
            "current_smv_path": current_smv_path})
        current_task.start()
        current_task.join()

    def run_script(self, dir, case, smv_path):
        """Run a particular script"""
        print("run", case.path, "with", smv_path, "in", dir)
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
                case_rundir, fds_prefix + ".smv", smv_path=smv_path)
            # open(stop_path(dest_script_path), 'w')

    def run_scripts(self, dir, smv_path):
        print("smv_path:", smv_path)
        return self.executor.map(self.run_script, itertools.repeat(dir), self.cases, itertools.repeat(smv_path))

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


if __name__ == "__main__":
    tcases = cases.get_cases('../../../smv/Verification/scripts/cases.json')

    main_suite = Suite(tcases)
    main_suite.run()
    main_suite.create_snapshot()

    comparison = Comparison(tcases)

    os.environ["SMOKEVIEW_OBJECT_DEFS"] = "/home/jake/smv-master/Build/smokeview/gnu_linux_64/objects.svo"

    comparison.run(base_smv_path="/home/jake/smv-master/.vscode/build/smokeview",
                   current_smv_path="/home/jake/smv/.vscode/build/smokeview")
    comparisons = comparison.compare_images()

    for diff in comparisons:
        print(diff["base"], diff["current"], diff["comparison"], diff["diff"])
