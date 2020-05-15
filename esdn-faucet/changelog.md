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
