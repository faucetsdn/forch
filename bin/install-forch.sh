#!/bin/ash

set -euo pipefail

APK="apk -q"
BUILDDEPS="gcc g++ python3-dev musl-dev parallel yaml-dev"
TESTDEPS="bitstring pytest wheel virtualenv"
PIP3="pip3 -q --no-cache-dir install --upgrade"
FROOT="/forch-src"

dir=$(dirname "$0")

${APK} add -U git ${BUILDDEPS}
${PIP3} pip
${PIP3} setuptools ${TESTDEPS}
${PIP3} -r ${FROOT}/etc/requirements.txt
git init ${FROOT}
${PIP3} ${FROOT}

pip3 uninstall -y ${TESTDEPS} || exit 1
for i in ${BUILDDEPS} ; do
    ${APK} del "$i" || exit 1
done

# Clean up
rm -r "${FROOT}"
