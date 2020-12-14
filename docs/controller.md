# Standalone Controller Container

* `bin/build_docker controller`
* Results in docker image `forch/controller`
* Running: `docker run -d --privileged $docker_volumes $docker_ports forch/controller`
  * useful volumes
    * `/etc/faucet`: Configuration directory for `faucet`.
    * `/etc/forch`: Configuration directory for `forch`.
  * exposed ports
    * 6553: OpenFlow port connecting to faucet.
    * 6554: OpenFlow port connecting to gauge.
    * 9019: Faucet NOAH json API.
* OpenFlow switch configuration
  * Each switch configured with two controllers:
    * Port-exposed-for-`6553`
    * Port-exposed-for-`6554`

```
ls -l config/faucet.yaml
docker_volumes="-v $PWD/config:/etc/faucet"
docker_ports="-p 6001:6653 -p 7001:6654"
docker run -d --privileged $docker_volumes $docker_ports forch/controller
```
