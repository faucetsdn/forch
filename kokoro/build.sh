#!/bin/bash
# Should be run through go/benz

set -eux

cd git/benz-build-source
sudo kokoro/setup.sh
sudo apt-get install tree

echo TAPTAP
echo "${TMPDIR}"
mkdir -p "${TMPDIR}/binary/"
mkdir -p "${TMPDIR}/glinux-build"

df -h /usr/local/google
ls -l /usr/local/google
ls -l /usr/local/google/build-debs/base-rodete-amd64.tgz.tmp || true

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
ls -l /usr/local/google/build-debs/base-rodete-amd64.tgz.tmp || true

cat forch/__version__.py

glinux-build -type="binary" -base-path="${TMPDIR}/glinux-build" -additional-repos="enterprise-sdn-faucet-core-unstable" -name="rodete" . "${TMPDIR}/binary/"
mkdir -p binary

#build-debs -b -L -d rodete

echo TAPTAP
df -h /usr/local/google
ls -l /usr/local/google
ls -l /usr/local/google/build-debs/base-rodete-amd64.tgz.tmp || true

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
    ls -l /usr/local/google/build-debs/base-rodete-amd64.tgz.tmp || true

    glinux-build -type="binary" -base-path="${TMPDIR}/glinux-build" -additional-repos="enterprise-sdn-faucet-core-unstable" -name="rodete" . "${TMPDIR}/binary/"
    mkdir -p binary

#    build-debs -b -L -d rodete || true
)

echo TAPTAP
df -h /usr/local/google || true
ls -l /usr/local/google || true
ls -l /usr/local/google/build-debs/base-rodete-amd64.tgz.tmp || true

#cp esdn-faucet/binary/* binary/
cp ${TMPDIR}/binary/* binary/
ls -l binary/
