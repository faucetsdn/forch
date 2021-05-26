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
faucet_bad=
for remote in faucet origin perry; do
    faucet_tag=`git ls-remote -t $remote | grep v1_0` || true
    if [ -n "$faucet_tag" ]; then
        bad_r=${bad_r}" $remote"
        faucet_bad=$faucet_tag" $faucet_tag"
    fi
done
faucet_tag=`git tag --list | grep v1_0` || true
if [ -n "$faucet_tag" ]; then
    bad_r=${bad_r}" local"
    faucet_bad=$faucet_tag" $faucet_tag"
fi
if [ -n "$bad_r" ]; then
    echo
    echo Error:
    echo Faucet tag found in Forch repos in: [ $bad_r ]
    echo $faucet_bad > .bad_tags
    echo All bad tags dumped to file .bad_tags
    false
fi

mtag=`git describe perry/master --abbrev=0`
gtag=`git describe perry/gmaster --abbrev=0`

mhash=`git rev-list -n 1 $mtag`
ghash=`git rev-list -n 1 $gtag`

mbase=`git merge-base $mtag perry/master`
gbase=`git merge-base $gtag perry/gmaster`

if [ $mbase != $mhash ]; then
    echo Merge base for master/$mtag does not match expected hash.
    false
fi

if [ $gbase != $ghash ]; then
    echo Merge base for gmaster/$gtag does not match expected hash.
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

echo
echo All remote tags are consistent.
