#!/bin/bash
# Should be run through go/benz

set -eux

cd git/benz-build-source
sudo kokoro/setup.sh
sudo apt-get install tree

echo TAPTAP
df -h /usr/local/google
ls -l /usr/local/google

FAUCET_VERSION=$(< etc/FAUCET_VERSION)
echo Fixing debian faucet version to $FAUCET_VERSION
fgrep -v $FAUCET_VERSION debian/control > /dev/null
sed -i s/FAUCET_VERSION/${FAUCET_VERSION}/ debian/control
fgrep $FAUCET_VERSION debian/control

VERSION=$(git describe)
debchange --newversion $VERSION -b "New upstream release"

# Write version content to __version__.py
cat >forch/__version__.py <<VER_FILE
"""Forch version file"""

__version__ = '$VERSION'
VER_FILE

echo TAPTAP
df -h /usr/local/google
ls -l /usr/local/google

cat forch/__version__.py
build-debs -b -L -d rodete

echo TAPTAP
df -h /usr/local/google
ls -l /usr/local/google

(
    cd esdn-faucet
    git checkout origin/esdn -- FORCH_VERSION
    FORCH_VERSION=$(< FORCH_VERSION)
    echo Fixing debian forch version to $FORCH_VERSION
    fgrep -v $FORCH_VERSION debian/control > /dev/null
    sed -i s/FORCH_VERSION/${FORCH_VERSION}/ debian/control
    fgrep $FORCH_VERSION debian/control

    VERSION=$(git describe remotes/origin/esdn)
    echo esdn-faucet version $VERSION
    debchange --newversion $VERSION -b "New upstream release"

    echo TAPTAP
    df -h /usr/local/google
    ls -l /usr/local/google

    build-debs -b -L -d rodete
)

echo TAPTAP
df -h /usr/local/google
ls -l /usr/local/google

cp esdn-faucet/binary/* binary/
ls -l binary/
