#!/bin/bash -e

print_usage()
{
   echo "Usage: "
   echo " * Building a release with a new Forch, no change in Faucet"
   echo "   ./build_release.sh release-new-forch-1 GIT-USERNAME FORCH-TAG ESDN-FAUCET-TAG"
   echo "   ./build_release.sh release-new-forch-2 GIT-USERNAME FORCH-TAG ESDN-FAUCET-TAG"
   echo "   ./build_release.sh release-new-forch-3"
   echo
   echo " * Misc helpers"
   echo "   ./build_release setup-forch-repo"
}

setup_forch_repo()
{
  # needs the git username as an argument
  [ "$#" -ne 1 ] && print_usage && return

  echo Setting up prodaccess
  prodaccess

  echo Checking out Forch repository
  git clone sso://perry-internal/forch forch-release
  cd forch-release

  echo Setting up remotes for github user $1
  git remote add faucet git@github.com:faucetsdn/forch.git
  git remote rm origin
  git remote add origin git@github.com:$1/forch.git
  git remote add perry sso://perry-internal/_direct/forch
  echo Setup complete
}

tag_forch()
{
  # needs the git username as an argument
  [ "$#" -ne 1 ] && print_usage && return

  echo Tagging Forch $1
  cd forch-release
  git fetch faucet
  git fetch perry
  echo Merging faucet/master to origin and pushing
  git checkout master
  git reset --hard faucet/master
  git push origin master
  git push faucet master
  git push perry master
  git tag -a $1 -m "Release $1"
  git checkout -b gmaster
  git merge $1
  git tag -a $1.1 -m "Release $1.1"
  git push perry gmaster
  git push --tags perry
  git push --tags faucet
  git push --tags origin
}

update_esdn_init()
{
  [ "$#" -ne 2 ] && print_usage && return
  echo Updating perry/esdn with Forch_Version $1 to build ESDN_RELEASE $2
  git checkout perry/esdn
  echo $1.1 > esdn-faucet/FORCH_VERSION
  echo Update esdn-faucet/changelog.md then continue with next phase of release
  echo "For logs: git log --oneline --decorate <prev tag>..<new tag>"
}

update_esdn_final()
{
  [ "$#" -ne 2 ] && print_usage && return
  echo Merging Forch release $1.1
  git merge $1.1
  git commit -am "Update Forch version to $1.1"
  git tag -a $2 -m "ESDN-Faucet release $2"
  git push perry $2
  git push --tags perry
  echo Check branches and tag consistency with kokoro/check.sh.
  echo Build with esdn-faucet/pkg_build.sh, and test it is good for promotion
}

rapture_promote_to_candidate()
{
  echo Capture rapture package delta for release notes:
  rapture diff enterprise-sdn.faucet.all-testing enterprise-sdn.faucet.all-unstable | egrep 'forch|faucet'
  echo Tagging build as candidate
  rapture settag enterprise-sdn-faucet-core-unstable enterprise-sdn-faucet-release.candidate:true
  rapture settag enterprise-sdn-faucet-forch-unstable enterprise-sdn-faucet-release.candidate:true
  echo Verify that the candidate versions below are accurate
  rapture listrepo enterprise-sdn-faucet-forch-candidate
  rapture listrepo enterprise-sdn-faucet-core-candidate
}

[ "$#" -lt 1 ] && print_usage && exit

case $1 in
  setup-forch-repo)
    [ "$#" -ne 2 ] && print_usage && false
    setup_forch_repo $2
    ;;
  release-new-forch-1)
    [ "$#" -ne 4 ] && print_usage && false
    setup_forch_repo $2
    tag_forch_func $3
    update_esdn_init $3 $4
    ;;
  release-new-forch-2)
    [ "$#" -ne 4 ] && print_usage && false
    update_esdn_final $3 $4
    ;;
  release-new-forch-3)
    rapture_promote_to_candidate
    ;;
  *)
    print_usage
    ;;
esac
