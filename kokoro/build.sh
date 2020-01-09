#!/bin/bash
#Should be run through go/benz

set -eux
ls -alrt git/
uname -a
cd git/benz-build-source
sudo kokoro/setup.sh
#mkdir binary/
#glinux-build -name="rodete" binary/

VERSION=$(git describe)
debchange --newversion $VERSION -b "New upstream release"

# write version content to __version__.py
cat >forch/__version__.py <<VER_FILE
"""Forch version file"""

__version__ = '$VERSION'
VER_FILE

cat forch/__version__.py
build-debs -b -L -d rodete
#cd
#sudo apt-get install tree
#tree
