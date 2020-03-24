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

echo ESDN_VERSION $ESDN_VERSION
echo FAUCET_VERSION $FAUCET_VERSION
echo FORCH_VERSION $FORCH_VERSION

prodaccess

yes | benz build --git -pool="rodete-huge" -sign -branch="$FAUCET_VERSION" -target-prefix=enterprise-sdn-faucet-core rpc://perry-internal/faucet &
yes | benz build --git -pool="rodete-huge" -sign -branch="$FORCH_VERSION" -target-prefix=enterprise-sdn-faucet-forch rpc://perry-internal/forch &

wait

echo
echo Build results:

echo Checkout output of: rapture listrepo enterprise-sdn.faucet.all-unstable
rapture listrepo enterprise-sdn.faucet.all-unstable | fgrep "esdn-faucet $ESDN_VERSION " || (echo Missing ESDN version $ESDN_VERSION && false)
rapture listrepo enterprise-sdn.faucet.all-unstable | fgrep "faucet $FAUCET_VERSION " || (echo Missing FAUCET verion $FAUCET_VERSION && false)
rapture listrepo enterprise-sdn.faucet.all-unstable | fgrep "forch $FORCH_VERSION " || (echo Missing FORCH version $FORCH_VERSION && false)

echo
echo Done with successful build.
