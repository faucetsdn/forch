## 1.13.0
## Forch 0.45
* Fix debian grpc depenancy (#182)
* Add grpc dependancy (#180)
* Consolidate test shards (#175)
* Improve stack test checking (#174)
* Connect port state manager to Forch orchestration components (#170)
* Add logging for gauge config file writting (#173)
* Fix local test run permissions (#172)
* Update dependency jsoneditor to v9.1.0 (#171)
* Add port state manager with port state machine for FOT (#165)
* Set logging level only for forch modules (#167)
* Update dependency jsoneditor to v9.0.5 (#155)
* Cleanup stale placements in faucetizer when restoring learned MACs (#166)
* Forch, Gauge inside faucet container (#164)
* Add gRPC interface to receive device testing results (#159)
## Faucet 1.9.48.2
* Flush varz and trigger expire event when vlan host caches get cleared
* WSAPI port changes to allow serving on 8080

## 1.12.0
## Forch 0.44
* Add loop detection logic and test (#160)
* Expose ryu config in API (#154)
* Fix test_access in Forch test suite (#158)
* Auto reload segemnts, static placements and static behaviors files (#153)
* Make LACP logs more verbose (#151)
* Change forch log os env in line with other faucet os envs. (#152)
* Enable Faucetizer to add VLAN config for unauthenticated VLAN (#150)
* Test device role that contains different types of symbols (#149)
* Enable Faucetizer sequester devices into testing VLANs (#143)
* Add testing/test_failscale for stack failover (#146)
* Add basic scaling test (#145)
* Simplify topo bond configuration (#144)
* Use DHCP for some containers (#140)
* Remove excess ports from dva tests (#142)
* Test OT trunks as part of integration tests (#141)
* Integration tests to setup stack and test connectivity (#138)
* Avoid empty acls_in for a port during DVA (#139)
## Faucet 1.9.48
* Don't send empty apply action instructions
* Add support for VLANs on a stack that aren't expressed on the root switch
* Fix LACP role metric was not updated when stack root changes
* Remove experimental API
* Export ryu_conf variables to as Prometheus metrics
* Gauge now clears all variables on config reload (so de-configured DP variables are removed)
* Update dependencies:
  * prometheus 2.20.0 [docker]
  * grafana 7.1.1 [apt, docker]
  * sphinx 3.1.2 [docs]
  * pytype 2020.7.30 [tests]


## 1.11.0
## Forch 0.43
* Avoid empty acls_in for a port during DVA (#139)
* Add github workflows for integration tests (#136)
* Create /etc/faucet/faucetat the end of Forch installation (#135)
* Expose faucet config warning through API and Varz (#133)

## 1.10.0
## Forch 0.42
* Make Forch manage gauge.yaml and reorganize files in integration tests (#131)

## 1.9.0
## Forch 0.41
* Output augmented include files to faucet directory (#129)
* Account for port role while calculating egress link state. Change is egress port to fix error querying lag state when varz are queried.  (#128)
* Reflect switch state cookie error in system state (#127)
* Use lowercase MAC addresses in Faucetizer (#126)
## Faucet 1.9.47
* Optimization: suppress unneeded overlapping OpenFlow delete messages.
* Do not allow overlapping interface ranges in configuration file.
* Add a prometheus variable for stack root status by datapath.
* Update dependencies
  * prometheus 2.19.2 [docker]
  * grafana 7.0.4 [apt, docker]
  * sphinx 3.1.1 [docs]
  * sphinx rtd theme 0.5.0 [docs]
  * pytype 2020.6.26 [tests]

## 1.8.0
## Forch 0.40
* Use lowercase MAC addresses in Faucetizer (#126)
* Augment ACLs in faucet.yaml and verify role-based ACLs existence (#125)
* Add ARP allow rule in initial VLAN ACL (#122)
* Add Forch varz for vlan packet counts (#123)
* Do not assert existence of access switch for a MAC (#124)
* Monitor packet rate for each VLAN (#121)
## Faucet 1.9.46
* Optimise out actions that won't have any effect (e.g. modify packet header before dropping it)
* Fix coprocessor traffic being subject to VLAN ACLs
* Move LACP implementation to switch manager classes
* Remove unneeded mininet dependency in unit tests

# 1.7.0
## Forch 0.39
* Check if port change event's port exists in dp config (#119)
* Add ACLs counting topo and corresponding tests (#118)
## Faucet 1.9.43
(same version as 1.6.0, see below)

# 1.6.0
## Forch 0.38
* Expose DVA state in NOAH API (#111)
* Change initial Faucet config behavior (#110)
* Expose RADIUS result info in NOAH (#112)
* Handle unexpected RADIUS responses. Accept learning events only if it doesn't exist in map (#109)
* Decouple device behavior from device placement in Faucetizer (#107)
* Add unit test framework and reorganize tests (#108)
* Monitor CPU percent of target processes (#105)
## Faucet 1.9.43
* Optimize stack reloading - don't take down stack ports on config restart, unless there was a topology change.
* Update dependencies:
  + grafana to v7.0.0 [apt, docker]
  + prometheus to v2.18.1 [docker]

# 1.5.0
## Forch 0.37
* Faucet version 1.9.42
* Make sessions dictionary thread safe (#102)
* Update learned mac metrics only for access port (#98)
* Log RADIUS retries in debug. (#96)
* Proxy server to serve up varz on various ports (#85)
* Add forch and faucet structural config to sys_config API (#94)
## Faucet 1.9.42
* Fix switches that require static table IDs.
* Faucet can now automatically generate non-colliding port IDs for LACP
* Added prometheus metric for exposing LACP Port ID.
## Faucet 1.9.41
* Add stack port/graph info to events when stack changes.
* Fix graph object in the STACK_TOPO_CHANGE event.
* Fix order of flow adds/mods not deterministic
## Faucet 1.9.40
* N/A -- there was no release
## Faucet 1.9.39
* Make edge_learn_stack_root the default stack learning algorithm
* Fix flows for tagged ports were being deleted on warm start

# 1.4.0
## Forch 0.36
* Cleanup logs (#95)
* Add forch and faucet structural config to sys_config API (#94)
* Change packet format for RADIUS requests to better suit what corpRADIUS
  expects and sends out (#91)
* Expose learned macs via Forch varz (#90)
* Make source port for RADIUS queries configurable (#92)
* Rev-parse fix
* Improve exception handling in processing event (#87)
* Load forch config file from FORCH_CONFIG_FILE (#86)
* Fix egress state traceback error (#84)
* Wait for RADIUS response before exiting when used as a standalone tool. (#83)
* Change topo/bond/faucet.yaml to replace interface_ranges and raise a hard
  exception when port is not defined in config. (#82)
* Change base dir of forch related files (#80)
* Set egress state to unkown if no LAG info is received (#79)
* Assign native_vlan to host ports based on forch unauthenticated_vlan
  configuration (#78)
* Change criteria for healthy egress state to include two active links. (#77)
* Expose ACL metrics in NOAH switch_state API (#68)
* Modify authenticator to function as a mab standalone script (#76)
* Automatically assign cookies to ACL rules (#73)
* Add process metrics (#71)

## Faucet 1.9.38
* Consolidate standalone/stacked learn/flood classes
* Add lacp_port_role prometheus metric
* Add lacp_port_priority setting for indicating port preference in a LACP bundle
* FAUCET can now learn from icmp requests to VIP
* Fix various hardware test suite flakes
  * LACP tests should ignore Linux LACP churn metric
  * Explicitly clear ARP cache in test hosts before pinging FAUCET VIP

# 1.3.0
## Forch 0.35
* Faucet 1.9.37
* Varz monitoring RADIUS responses and timeouts (#69)
* Update dependency jsoneditor to v8.6.4 (#70)
* Pin python3 to 3.7
* Remove auth.yaml dependency (#67)
* Update ubuntu Docker tag to v20 (#53)
* Make faucetizer output behavior configurable (#63)
* Tweaks to improve forch test stability (#66)
* Forch varz interface with basic varz (#64)
* Remove restart_type related metrics from NOAH API (#62)
* Modify authenticator to function as a mab standalone script (#76)
* Change base dir of forch related files (#80)

## Faucet 1.9.37
* Lacp_standby 
## Faucet 1.9.36
* Fix DP level config changes not detected
* Add support for ordered ACL actions

# 1.2.0
## Forch 0.34
* Faucet 1.9.35
* Move Forch binary entry point to forch/__main__.py (#54)
* Complete protobuf conversion of forch config (#60)
* Add RADIUS secret handler (#58)
## Faucet 1.9.35
* Changing port description shouldn't trigger cold-restart of a dataplane.
* Setting drop_spoofed_faucet_mac to false as a workaround no longer required on stacked/routed networks.
* Fault tolerance test verifies controller has detected link fault before proceeding

# 1.1.0
## Forch 0.33
* Faucet 1.9.34
* Expose DVA state in NOAH (#45)
* Ignore dynamic auth result for devices in static file (#43)
* Add timeouts to session states (#40)
* Add socket connection stats (#36)
* Forch initialization enhancements (#28)
* Handle L2_EXPIRE events (#27)
* Update Faucetizer to periodically read and write faucet config (#17)
## Faucet 1.9.34
* Add better diagnostics for LACP state
* Fix Gauge logging spurious "no response" message when prometheus mode is enabled
