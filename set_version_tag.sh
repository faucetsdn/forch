#!/bin/bash -eu

tag=$1
if [[ -z $tag ]]; then
  echo "Tag is empty.\nUsage: ./set_version_tag.sh <tag>"
  exit
fi

FAUCET_VERSION=$(< etc/FAUCET_VERSION)
echo Fixing debian faucet version to $FAUCET_VERSION
fgrep -v $FAUCET_VERSION debian/control > /dev/null
sed -i "s/python3-faucet.*/python3-faucet (= $FAUCET_VERSION),/" debian/control
fgrep $FAUCET_VERSION debian/control

VERSION=$tag
debchange --newversion $VERSION -b "New upstream release $tag"

# Write version content to __version__.py
cat >forch/__version__.py <<VER_FILE
"""Forch version file"""

__version__ = '$VERSION'
VER_FILE

cat forch/__version__.py

# Change ID hook
hook=`git rev-parse --git-dir`/hooks/commit-msg
mkdir -p $(dirname $hook)
curl -Lo $hook https://gerrit-review.googlesource.com/tools/hooks/commit-msg
chmod +x $hook

git add debian/changelog debian/control forch/__version__.py
git commit -m "Set version $tag in changelog"
git tag -a $tag -m "Release $tag"
more debian/changelog
