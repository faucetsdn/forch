#!/bin/bash
#Should be run through go/benz

set -eux
ls -alrt git/
uname -a
cd git/benz-build-source
sudo kokoro/setup.sh
#mkdir binary/
#glinux-build -name="rodete" binary/
debchange --newversion $(git describe) -b "New upstream release"
#build-debs -b -L -d rodete
#cd
#sudo apt-get install tree
#tree
mkdir -p "${TMPDIR}/binary/"
mkdir -p "${TMPDIR}/glinux-build"
glinux-build -type="binary" -base-path="${TMPDIR}/glinux-build" -additional-repos="enterprise-sdn-faucet-core-unstable" -name="rodete" . "${TMPDIR}/binary/"
cp ${TMPDIR}/binary/* binary/
ls -alrt
