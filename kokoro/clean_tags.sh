#!/bin/bash -e

echo faucet `git remote get-url faucet`
echo origin `git remote get-url origin`
echo pperry `git remote get-url perry`

echo Fetching remotes and tags...
for remote in faucet origin perry; do
    git fetch $remote
    for branch in master gmaster; do
        if [ $remote != faucet -o $branch != gmaster ]; then
            git fetch --tags $remote $branch
        fi
    done
done

# use the first faucet commit to get all the tags that are faucet, and delete
# them from origin, perry and faucetsdn.
for tag in `git tag --contains 91bab3bf39`; do
    for remote in faucet perry origin; do
        echo Deleting Faucet tag $tag from $remote
        git push --delete $remote $tag
    done
done

# clean up in local repo. delete all tags and fetch the right set
git tag -d $(git tag)
git fetch --tags

# check if everything is clean
faucet_tag=`git tag --list | fgrep v1_0`
if [ -n "$faucet_tag" ]; then
    echo Error faucet tag detected
    false
fi
