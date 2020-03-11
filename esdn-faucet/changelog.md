
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
