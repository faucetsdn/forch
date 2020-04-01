
# Next Release
  * ???
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
## Faucet 1.9.37
* lacp_standby 
