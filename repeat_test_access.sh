#!/bin/bash

role='"yellow"'
echo $role
while [ $role == '"yellow"' ]
do
    bin/net_clean; bin/setup_stack local skip-conn-check dva; bin/run_test_set access
    role=$(jq '.eth_srcs."9a:02:57:1e:8f:03".radius_result.role' test_out/dva-vlan-assigned/list_hosts.json)
done
