#!/bin/bash -e

echo faucet `git remote get-url faucet`
echo origin `git remote get-url origin`
echo pperry `git remote get-url perry`

echo Fetching remotes...
for remote in faucet origin perry; do
    git fetch $remote
    for branch in master gmaster; do
	if [ $remote != faucet -o $branch != gmaster ]; then
	    git fetch --tags $remote $branch
	fi
    done
done

# Check if faucet tags were added into forch, in remote or local
bad_r=""
for remote in faucet origin perry; do
    faucet_tag=`git ls-remote -t $remote | grep v1_0` || true
    if [ -n "$faucet_tag" ]; then
        bad_r=${bad_r}" $remote"
    fi
done
faucet_tag=`git tag --list | grep v1_0` || true
if [ -n "$faucet_tag" ]; then
    bad_r=${bad_r}" local"
fi
if [ -n "$bad_r" ]; then
    echo
    echo Error:
    echo Faucet tag found in Forch repos in: [ $bad_r ]
    echo
    false
fi

mtag=`git describe perry/master --abbrev=0`
gtag=`git describe perry/gmaster --abbrev=0`
etag=`git describe perry/esdn --abbrev=0`

mhash=`git rev-list -n 1 $mtag`
ghash=`git rev-list -n 1 $gtag`
ehash=`git rev-list -n 1 $etag`

mbase=`git merge-base $mtag perry/master`
gbase=`git merge-base $gtag perry/gmaster`
ebase=`git merge-base $etag perry/esdn`

if [ $mbase != $mhash ]; then
    echo Merge base for master/$mtag does not match expected hash.
    false
fi

if [ $gbase != $ghash ]; then
    echo Merge base for gmaster/$gtag does not match expected hash.
    false
fi

if [ $ebase != $ehash ]; then
    echo Merge base for esdn/$etag does not match expected hash.
    false
fi

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
    echo origin esdn: $oe
    echo pperry esdn: $pe
    false
fi

if [ -z "$oe" ]; then
    echo Unknown tag $etag
    false
fi

mbase=`git merge-base $gtag $etag`
mref=`git rev-list -n 1 $gtag`
if [ "$mbase" != "$mref" ]; then
    echo
    echo Error:
    echo "  git merge-base $gtag $etag"
    echo does not match expected gmaster tag $gtag
    echo
    false
else
    echo Merge-base of $gtag and perry/master is $mtag
fi

echo
echo All remote tags are consistent.
