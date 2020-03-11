#!/bin/bash -e

diffs=$(git status -s)

if [ -n "$diffs" ]; then
  echo Local differences found, please commit/clean before build.
  git status -s
  exit 1
fi

FORCH_VERSION=$(< esdn-faucet/FORCH_VERSION)
FAUCET_VERSION=$(git show $FORCH_VERSION:etc/FAUCET_VERSION)
ESDN_VERSION=$(git describe)

echo FAUCET_VERSION $FAUCET_VERSION
echo FORCH_VERSION $FORCH_VERSION
echo ESDN_VERSION $ESDN_VERSION

prodaccess

benz build --git -pool="rodete-huge" -sign -branch="$FAUCET_VERSION" -target-prefix=enterprise-sdn-faucet-core rpc://perry-internal/faucet
benz build --git -pool="rodete-huge" -sign -branch="$FORCH_VERSION" -target-prefix=enterprise-sdn-faucet-forch rpc://perry-internal/forch

rapture listrepo enterprise-sdn.faucet.all-unstable | egrep '(faucet|forch)'

