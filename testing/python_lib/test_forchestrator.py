"""Unit tests for Faucet State Collector"""

import unittest
import yaml
from unit_base import ForchestratorTestBase


class ForchestratorUnitTestCase(ForchestratorTestBase):
    """Test cases for dataplane state"""

    #pylint: disable=protected-access
    def test_faucet_config_validation(self):
        """Test validation for faucet config"""
        print(self._forchestrator)
        faucet_config_str = """
        dps:
          nz-kiwi-t1sw1:
            dp_id: 177
            faucet_dp_mac: 0e:00:00:00:01:01
            hardware: Generic
            lacp_timeout: 5
            stack:
              priority: 1
            interfaces:
              4:
                description: trunk
                tagged_vlans: [272]
              5:
                description: mirror
                tagged_vlans: [171]
              6:
                description: "to t1sw2 port 6"
                stack: {dp: nz-kiwi-t1sw2, port: 6}
              9:
                description: "to t2sw1 port 50"
                stack: {dp: nz-kiwi-t2sw1, port: 50}
              10:
                description: "to t2sw2 port 50"
                stack: {dp: nz-kiwi-t2sw2, port: 50}
              11:
                description: "to t2sw3 port 50"
                stack: {dp: nz-kiwi-t2sw3, port: 50}
              28:
                description: egress
                lacp: 3
                tagged_vlans: [171]
            lldp_beacon: {max_per_interval: 5, send_interval: 5}"""
        faucet_config = yaml.safe_load(faucet_config_str)
        self.assertFalse(self._forchestrator._validate_config(faucet_config))



if __name__ == '__main__':
    unittest.main()
