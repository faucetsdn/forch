#!/bin/bash
#Should be run through go/benz

set -eux
ls -alrt git/
uname -a
cd git/benz-build-source
sudo kokoro/setup.sh
#mkdir binary/
#glinux-build -name="rodete" binary/
debchange --newversion $(git describe --tags $(git rev-list --tags --max-count=1)) -b "New upstream release"
build-debs -b -L -d rodete
#cd
#sudo apt-get install tree
#tree
