#!/bin/bash
set -x

# Remove iptables rules
sudo iptables -t nat -D OUTPUT -o dummy0 -p udp -m udp --dport 4789 -j REDIRECT --to-ports 20000 || true
sudo iptables -t nat -D POSTROUTING -d 127.0.0.1/32 -p udp -m udp --dport 4789 -j SNAT --to-source 192.168.21.1:38000-45000 || true

# Kill socat processes
kill `ps ax | grep socat | grep 30001 | awk '{print $1}'` || true
kill `ps ax | grep socat | grep 30000 | awk '{print $1}'` || true

# Delete interfaces
sudo ip link set vxlan down || true
sudo ip link del vxlan || true

sudo ip link set dummy0 down || true
sudo ip link del dummy0 || true
