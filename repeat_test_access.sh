#!/bin/bash

role=0
echo $role
while [ $role == 0 ]
do
    bin/net_clean; bin/setup_stack local skip-conn-check dva; bin/run_test_set access
    role=$(jq '.switches."nz-kiwi-t2sw3".ports."1".acls[0].rules[0].packet_count' test_out/dva-port-down/switch_state.json)
done
