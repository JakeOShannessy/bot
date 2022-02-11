#!/bin/bash

#---------------------------------------------
#                   usage
#---------------------------------------------

function usage {
echo ""
echo "make_manuals.sh usage"
echo ""
echo "This script builds FDS manuals"
echo ""
echo "Options:"

FIREBOT_HOME_MSSG=
if [ "$FIREBOT_HOME" != "" ]; then
  FIREBOT_HOME_MSSG="[default: $FIREBOT_HOME]"
fi
echo "-d dir - firebot home directory $FIREBOT_HOME_MSSG"

FIREBOT_REPOHOME_MSSG=
if [ "$FIREBOT_REPOHOME" != "" ]; then
  FIREBOT_REPOHOME_MSSG="[default: $FIREBOT_REPOHOME]"
fi
echo "-D dir - firebot repo home directory $FIREBOT_REPOHOME_MSSG"
echo "-F - fds repo hash/release"
echo "-h - display this message"

FIREBOT_HOST_MSSG=
if [ "$FIREBOT_HOST" != "" ]; then
  FIREBOT_HOST_MSSG="[default: $FIREBOT_HOST]"
fi
echo "-H host - firebot host $FIREBOT_HOST_MSSG"

if [ "$MAILTO" != "" ]; then
  echo "-m mailto - email address [default: $MAILTO]"
else
  echo "-m mailto - email address"
fi
echo "-r - create manuals using a release branch name"
exit 0
}

#---------------------------------------------
#                   CHK_REPO
#---------------------------------------------

CHK_REPO ()
{
  local repodir=$1

  if [ ! -e $repodir ]; then
     echo "***error: the repo directory $repodir does not exist."
     echo "          Aborting the make_bundle script"
     return 1
  fi
  return 0
}

#---------------------------------------------
#                   CD_REPO
#---------------------------------------------

CD_REPO ()
{
  local repodir=$1
  local branch=$2

  CHK_REPO $repodir || return 1

  cd $repodir
  if [ "$branch" != "current" ]; then
  if [ "$branch" != "" ]; then
     CURRENT_BRANCH=`git rev-parse --abbrev-ref HEAD`
     if [ "$CURRENT_BRANCH" != "$branch" ]; then
       echo "***error: was expecting branch $branch in repo $repodir."
       echo "Found branch $CURRENT_BRANCH. Aborting firebot."
       return 1
     fi
  fi
  fi
  return 0
}

#-------------------- start of script ---------------------------------

if [ -e $HOME/.bundle/bundle_config.sh ]; then
  source $HOME/.bundle/bundle_config.sh
else
  echo ***error: configuration file $HOME/.bundle/bundle_config.sh is not defined
  exit 1
fi
FIREBOT_HOST=$bundle_hostname
FIREBOT_HOME=$bundle_firebot_home
FIREBOT_REPOHOME=$bundle_firebot_repohome

MAILTO=
if [ "$EMAIL" != "" ]; then
  MAILTO=$EMAIL
fi
FDS_RELEASE=
SMV_RELEASE=
ECHO=
PROCEED=
UPLOAD=-g

FORCE=
RELEASE=
BRANCH=nightly

while getopts 'd:D:F:hH:m:r' OPTION
do
case $OPTION  in
  d)
   FIREBOT_HOME="$OPTARG"
   ;;
  D)
   FIREBOT_REPOHOME="$OPTARG"
   ;;
  F)
   FDS_RELEASE="$OPTARG"
   ;;
  h)
   usage
   ;;
  H)
   FIREBOT_HOST="$OPTARG"
   ;;
  m)
   MAILTO="$OPTARG"
   ;;
  r)
   BRANCH=release
   ;;
esac
done
shift $(($OPTIND-1))

echo ""
echo "------------------------------------------------------------"
echo "            Firebot host: $FIREBOT_HOST"
echo "  Firebot home directory: $FIREBOT_HOME"
if [ "$FDS_RELEASE_ARG" != "" ]; then
  echo "            FDS TAG/HASH: $FDS_RELEASE"
fi
echo "                   EMAIL: $MAILTO_ARG"
echo "          Firebot branch: $FIREBOT_BRANCH_ARG"
echo "------------------------------------------------------------"
echo ""

curdir=`pwd`

commands=$0
DIR=$(dirname "${commands}")
cd $DIR
DIR=`pwd`

#define fdsrepo location
cd ../..
repo=`pwd`
fdsrepo=$repo/fds
botrepo=$repo/bot

#***clone fds repo
echo cloning fds repo using tag/hash: $FDS_RELEASE
cd $botrepo/Scripts
./setup_repos.sh -G

cd $fdsrepo
echo git checkout -b $BRANCH $FDS_RELEASE
git checkout -b $BRANCH $FDS_RELEASE
git describe --dirty --long
git branch -a

cd $curdir

#***copy figures
cd $curdir
echo "./Copy_Figures.sh -H $FIREBOT_HOST -d $FIREBOT_REPOHOME/fds -v"
./Copy_Figures.sh -H $FIREBOT_HOST -d $FIREBOT_REPOHOME/fds -v


#*** generate manuals

cd $botrepo/Firebot
./run_firebot.sh -f -M -b

cd $CURDIR
