
# Next Release
  * 1.3.0
# 1.2.0
## Forch 0.34
* Faucet 1.9.35
* Move Forch binary entry point to forch/__main__.py (#54)
* Complete protobuf conversion of forch config (#60)
* Add RADIUS secret handler (#58)
## Faucet 1.9.35
Changing port description shouldn't trigger cold-restart of a dataplane.
Setting drop_spoofed_faucet_mac to false as a workaround no longer required on stacked/routed networks.
Fault tolerance test verifies controller has detected link fault before proceeding
