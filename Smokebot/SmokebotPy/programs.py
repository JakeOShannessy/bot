import tempfile
import subprocess
import os
import re
import platform


def run(program, directory, filename, processes=None):
    print("running", filename)
    cmd = "fds6.9.1"
    if program == "cfast":
        cmd = "cfast7.7.3"
    args = [cmd, filename]
    if processes:
        args.append("-p")
        args.append(processes)
    subprocess.run(args, shell=False,
                   capture_output=False, text=True, cwd=directory)
    print("completed", filename)


def git_clone(url, path, branch):
    print("cloning", url, "to", path)
    args = ["git", "clone", url, path, "--depth", "1"]
    if branch:
        args += ["-b", branch]
    subprocess.run(args, shell=False,
                   capture_output=False, text=True,)


def git_get_hash(url, branch) -> str:
    args = ["git", "ls-remote", url]
    if branch:
        args += ["--branch", branch]
    out = subprocess.run(args, shell=False,
                         capture_output=True, text=True)
    return out.stdout.split()[0]


def setup_cmake(path, build_path, release=False):
    print("cmake setup for", path)
    os.makedirs(build_path, exist_ok=True)
    args = ["cmake", "-B", build_path, "-S", path]
    if release:
        args.append("-DCMAKE_BUILD_TYPE=Release")
    else:
        args.append("-DCMAKE_BUILD_TYPE=Debug")
    if platform.system() == "Windows":
        args.append("-DVCPKG_TARGET_TRIPLET=x64-windows-static")
        args.append("-DVCPKG_HOST_TRIPLET=x64-windows-static")
        args.append(
            "-DCMAKE_TOOLCHAIN_FILE=C:/Users/josha/Documents/vcpkg/scripts/buildsystems/vcpkg.cmake")
    print(args)
    result = subprocess.run(args, shell=False,
                            capture_output=False, text=True,)
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        raise Exception(f'cmake setup failed')


def run_cmake(path, build_path):
    print("cmake build for", path)
    args = ["cmake", "--build", build_path]
    result = subprocess.run(args, shell=False,
                            capture_output=False, text=True,)
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        raise Exception(f'cmake build failed')


def install_cmake(build_path, install_prefix,release=False):
    args = ["cmake", "--install", build_path, "--prefix", install_prefix]
    if release:
        args += ["--config", "Release"]
    else:
        args += ["--config", "Debug"]
    result = subprocess.run(args, shell=False,
                            capture_output=False, text=True,)
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        raise Exception(f'cmake install failed')


def run_smv_script(directory, filename, smv_path="smokeview", objpath=None):
    env = None
    if objpath:
        env = os.environ.copy()
        env["SMOKEVIEW_OBJECT_DEFS"] = os.path.abspath(objpath)
    args = [os.path.abspath(smv_path), "-runscript", filename]
    result = subprocess.run(args, shell=False,
                            capture_output=True, text=True, cwd=directory, env=env)
    if result.returncode != 0:
        print("stderr:",result.stderr)
        print("stdour:",result.stdout)
    (fdsprefix,ext) = os.path.splitext(os.path.basename(filename))
    with open(f"{os.path.join(directory,fdsprefix)}.stderr", 'w') as f:
        f.write(result.stderr)
    with open(f"{os.path.join(directory,fdsprefix)}.stdout", 'w') as f:
        f.write(result.stdout)
    return result


cmp_regex = re.compile('[^\\(]*\\((.*)\\)')


def compare_images(image1, image2, out_path) -> float:
    comparer = ImageComparer(image1, image2, out_path)
    return comparer.compare_images()


class ImageComparer():
    def __init__(self, image1, image2, out_path):
        self.dir = tempfile.TemporaryDirectory()
        self.image1 = image1
        self.image2 = image2
        self.out_path = out_path

    def compare_images(self) -> float:
        blur1 = os.path.join(self.dir.name, "blur1.png")
        blur2 = os.path.join(self.dir.name, "blur2.png")
        intermediate_path = os.path.join(self.dir.name, "inter1.png")
        self.blur_image(self.image1, blur1)
        self.blur_image(self.image2, blur2)
        args = ["magick", "compare", "-metric",
                "rmse", blur1, blur2, intermediate_path]
        os.makedirs(os.path.dirname(self.out_path), exist_ok=True)
        output = subprocess.run(args, shell=False,
                                capture_output=True, text=True, cwd=".")
        diff = None
        m = cmp_regex.match(output.stderr)
        if m:
            diff = float(m.group(1))
        inter3 = os.path.join(self.dir.name, "out1.png")
        self.composite_image(blur1, blur2, inter3, diff)
        inter5a = os.path.join(self.dir.name, "inter5a.png")
        self.annotate_image(self.image1, inter5a, "Base")
        inter5b = os.path.join(self.dir.name, "inter5b.png")
        self.annotate_image(self.image2, inter5b, "Current")
        subprocess.run(["magick", "montage", inter5a, inter5b, inter3, "-geometry", "+3+1", self.out_path], shell=False,
                       capture_output=False, text=True, cwd=".")
        return diff

    def annotate_image(self, input, output, label):
        args = ["magick", input, "-gravity", "Center", "-pointsize",
                "24", f"label:{label}", "-append"]
        args.append(output)
        if os.path.dirname(output):
            os.makedirs(os.path.dirname(output), exist_ok=True)
        subprocess.run(args, shell=False,
                       capture_output=False, text=True, cwd=".")

    def blur_image(self, input, output):
        args = ["magick", input, "-blur", "0x2"]
        args.append(output)
        if os.path.dirname(output):
            os.makedirs(os.path.dirname(output), exist_ok=True)
        subprocess.run(args, shell=False,
                       capture_output=False, text=True, cwd=".")

    def composite_image(self, input1, input2, output, diff):
        inter2 = os.path.join(self.dir.name, "inter2.png")
        args = ["magick", "composite", input1,
                input2, "-compose", "difference", inter2]
        if os.path.dirname(output):
            os.makedirs(os.path.dirname(output), exist_ok=True)
        subprocess.run(args, shell=False,
                       capture_output=False, text=True, cwd=".")
        args2 = ["magick", inter2, "-channel", "RGB", "-negate"]
        if diff != None:
            args2 += ["-gravity", "Center", "-pointsize",
                      "24", f"label:rmse: {diff}", "-append"]
        args2.append(output)
        subprocess.run(args2, shell=False,
                       capture_output=False, text=True, cwd=".")
