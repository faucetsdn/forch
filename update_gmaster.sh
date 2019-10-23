#!/bin/bash -e

# Update this to reflect the feature branches that should be merged in.
PROJ=forch
BRANCHES="blocking"

TMP_SH=/tmp/update_gmaster.sh
BASE=`git rev-parse --show-toplevel`
BASE_SH=$BASE/update_gmaster.sh
VTEMP=/tmp/GVERSION
VFILE=$BASE/$PROJ/GVERSION
date > $VTEMP
REPO=sso://perry-internal/faucet

if [ $0 != $TMP_SH ]; then
    echo Running out of $TMP_SH to mask local churn...
    cp $0 $TMP_SH
    $TMP_SH; false
fi

branch=`git rev-parse --abbrev-ref HEAD`
if [ "$branch" != "gupdater" ]; then
    echo $0 should be run from the gupdater branch.
    false
fi

files=`git status --porcelain`
if [ -n "$files" ]; then
    echo Local changes detected:
    echo $files
    echo Please resolve before updating.
    false
fi

ORIGIN=`git remote -v | egrep ^origin | fgrep fetch | awk '{print $2}'`
echo origin $ORIGIN >> $VTEMP
if [ "$ORIGIN" != "$REPO" ]; then
    echo git origin $ORIGIN does not match expected $REPO
    false
fi

echo Fetching remote repos...
git fetch origin

LOCAL=`git rev-parse gupdater`
echo $LOCAL gupdater >> $VTEMP
REMOTE=`git rev-parse origin/gupdater`
if [ "$LOCAL" != "$REMOTE" ]; then
    echo gupdater out of sync with upstream origin/gupdater
    false
fi

echo Switching to gmaster branch...
git checkout gmaster

echo Creating clean clone of master...
git reset --hard origin/master
echo `git rev-parse HEAD` master >> $VTEMP

echo Merging feature branches...
for branch in $BRANCHES; do
    echo Merging origin/$branch...
    git merge --no-edit origin/$branch
    echo `git rev-parse origin/$branch` $branch >> $VTEMP
done

echo `git rev-parse HEAD` gmaster >> $VTEMP
cp $VTEMP $VFILE
git add $VFILE
git commit -m "Adding version history"

echo Done with clean gmaster merge.
echo You will likely need to force push.
