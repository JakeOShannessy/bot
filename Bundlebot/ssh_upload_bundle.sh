#!/bin/bash
filebase=$1
NIGHTLY=$2
platform=$3
upload_dir=$4

fullfile=$HOME/.bundle/bundles/${filebase}.sh

if [ "$UPLOAD_HOST" == "" ]; then
  echo "***warning: UPLOAD_HOST is not defined"
fi
if [ ! -e $fullfile ]; then
  echo "***warning: the file $fullfile does not exist"
fi
if [ "$UPLOAD_HOST" != "" ]; then
  if [ -e $fullfile ]; then
    curdir=`pwd`
    scp -q upload_bundle.sh $UPLOAD_HOST\:.bundle/bundles/.
    cd $HOME/.bundle/bundles
    scp -q ${filebase}.sh            $UPLOAD_HOST\:.bundle/bundles/.
    scp -q ${filebase}.sha1_repodate $UPLOAD_HOST\:.bundle/bundles/.
    ssh -q $UPLOAD_HOST \( cd .bundle/bundles \; bash ./upload_bundle.sh \$HOME/.bundle/bundles $filebase $NIGHTLY $platform $upload_dir \)
    ssh -q $UPLOAD_HOST rm .bundle/bundles/upload_bundle.sh
    cd $curdir
  fi
fi
