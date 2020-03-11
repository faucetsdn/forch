#!/bin/bash -e

echo faucet `git remote get-url faucet`
echo origin `git remote get-url origin`
echo pperry `git remote get-url perry`

echo Fetching remotes...
git fetch --tags faucet master
git fetch --tags origin master
git fetch --tags origin gmaster
git fetch --tags perry master
git fetch --tags perry gmaster

mtag=`git describe perry/master`
gtag=`git describe perry/gmaster`
etag=`git describe perry/esdn`

echo Checking remote master tag $mtag
fm=`git ls-remote faucet $mtag`
om=`git ls-remote origin $mtag`
pm=`git ls-remote perry $mtag`

if [ "$fm" != "$om" ]; then
    echo faucet master: $fm
    echo origin master: $om
    false
fi

if [ "$fm" != "$pm" ]; then
    echo faucet master: $fm
    echo pperry master: $pm
    false
fi

if [ -z "$om" ]; then
    echo Unknown tag $mtag
    false
fi

echo Checking remote gmaster tag $gtag
og=`git ls-remote origin $gtag`
pg=`git ls-remote perry $gtag`

if [ "$og" != "$pg" ]; then
    echo origin gmaster: $og
    echo pperry gmaster: $pg
    false
fi

if [ -z "$og" ]; then
    echo Unknown tag $gtag
    false
fi

echo Checking remote esdn tag $etag
oe=`git ls-remote origin $etag`
pe=`git ls-remote perry $etag`
if [ "$oe" != "$pe" ]; then
    echo origin gmaster: $oe
    echo pperry gmaster: $pe
    false
fi

if [ -z "$oe" ]; then
    echo Unknown tag $etag
    false
fi

echo All remote tags are consistent.
