#  Building Bundles

### Overview

This directory contains scripts for building FDS/Smokeview installation files or bundles for Windows, Linux and OSX (Mac) computers.
Two bundle variations are built.  Bundles are built nightly using the fds and smv revisions from the latest firebot pass. 
Bundles are also built whenever FDS and Smokeview are released.

Building a bundle consists of three steps: 
  1. run firebot to generate FDS manuals, 
  2. run smokebot to generate Smokeview manuals 
  3. assemble applications, example files and manuals to generate the bundles.
These steps are described in more detail below.

### Bundling Steps

> [!CAUTION]
> These scripts erase and clone fresh copies of the fds and smv repos. You should only run these scripts in repos where you do not do daily work.

1. Run firebot on a Linux computer to generate FDS manuals. 
If firebot is successful (no errors or warnings), documents are copied to the
$HOME/.firebot/pubs and $HOME/.firebot/branch_name/pubs directories. At NIST this occurs every night.
The manuals for the FDS 6.7.6 release were generated using the script `build_fds_manuals.sh`. This script runs
firebot with the options 
`-x 5064c500c -X FDS6.7.6` for specifying the fds revision and tag  and options `-y a2687cda4 -Y SMV6.7.16`  for 
specifying the smv repo revision and tag. The tags are only created in the local fds and smv repos.  
They are not pushed up to github.
If errors are discovered in the bundles that require more commits a tag does not need to be undone.
Tagging is done by hand when the bundles are eventually published.  
The  parameter `-R release` is also passed to firebot to name the branch `release`.
It takes about seven hours to run firebot and build the fds manuals.
2. Run smokebot on a Linux computer to generate Smokeview manuals. If smokebot is successful,
documents are copied to `$HOME/.smokebot/pubs` and `$HOME/.smokebot/branch_name/pubs`. 
At NIST this occurs whenever the FDS and/or Smokeview source changes and also also once a day.
The manuals for the SMV 6.7.16 release were generated using the script `build_smv_manuals.sh`. Similar ot firebot, this script ran
smokebot with 
`-x 5064c500c -X FDS6.7.6` for specifying the fds revision and tag  and with `-y a2687cda4 -Y SMV6.7.16`  for 
specifying the smv repo revision and tag. The  parameter `-R release` is also passed to smokebot to name the branch `release`.
It takes about one hour to run smokebot and build the manuals.
3. Run the script `build_release.sh` on a Linux or OSX computer or `build_release.bat` on a Windows computer
to build the applications and bundle.  After building the bundles, these scripts upload them to the 
GitHub [test_bundles](https://github.com/firemodels/test_bundles) repository so that they can be tested before being published.

The bash script `build_release.sh` is used to build release bundles on a Linux or Mac computer.
It contains the following line for building the FDS6.7.6 and Smokeview 6.7.16 release bundle. Edit this
file and change the fds and smv hash and tags for a different release. `bundle_settings.sh` contains setttings such as
host names and email addresses particular to the site where the bundle is being generated. 
A sample settings script, `bundle_settings_sample`
is located in this directory.

```./run_bundlebot.sh -f -P $HOME/.bundle/bundle_settings.sh -R release -F 5064c500c -X FDS6.7.6 -S 485e0cd19 -Y SMV6.7.16 ```

Similarly, the windows batch file, `build_release.bat` contains the line

```run_bundlebot -c -R release -F 5064c500c -X FDS6.7.6 -S 485e0cd19 -Y SMV6.7.16```

for building a Windows bundle.  Edit this
file and change the fds and smv hash and tags for a different release.

### Summary

> [!CAUTION]
> It is worth repeating that these scripts erase and clone fresh copies of the fds and smv repos.  You should only run these scripts in repos where you do not do daily work.

1. Edit build_fds_manuals.sh, build_smv_manuals.sh, build_release.sh and build_release.bat updating hashes and tags.  
Commit these files.
3. Run build_fds_manuals.sh in firebot account.
4. Run build_smv_manuals.sh in smokebot account.
5. After manuals are built, run build_release.sh on both a Linux and Mac computer.  Run build_release.bat on a Mac.
 




