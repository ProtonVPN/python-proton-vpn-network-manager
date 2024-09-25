#!/usr/bin/env bash

if [[ "$CI" == "true" ]]
then
  # Only run these commands in CI
  # The following dir is required by the system bus dbus daemon.
  sudo mkdir -p /var/run/dbus
  # Run system bus dbus daemon as it's required by NetworkManager.
  sudo dbus-daemon --config-file=/usr/share/dbus-1/system.conf --print-address
  # Run network manager as it's required by the integration tests.
  NetworkManager
fi

python3 -m pytest tests/integration/killswitch/wireguard/test_killswitch_connection.py
