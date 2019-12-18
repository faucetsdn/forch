#!/bin/bash
#Should be run through go/benz

set -eux
ls -alrt git/
uname -a
echo "${TMPDIR}"
cd git/benz-build-source
sudo kokoro/setup.sh
ls -alrt /
#build-debs -b -L -d rodete
mkdir -p "${TMPDIR}/binary/"
mkdir -p "${TMPDIR}/glinux-build"
debchange --newversion $(git describe) -b "New upstream release"
glinux-build -type="binary" -base-path="${TMPDIR}/glinux-build" -additional-repos="enterprise-sdn-faucet-core-unstable" -name="rodete" . "${TMPDIR}/binary/"
mkdir -p binary
cp ${TMPDIR}/binary/* binary/
#cp ${TMPDIR}/binary/*.deb binary/
#cp ${TMPDIR}/binary/*.build binary/
#cp ${TMPDIR}/binary/*.buildinfo binary/
#cp ${TMPDIR}/binary/*.changes binary/
ls -alrt

