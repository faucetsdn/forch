"""Device state manager interface"""

import abc


class DeviceStateManager(abc.ABC):
    """An interface collecting the methods that manage device state"""
    @abc.abstractmethod
    def process_device_placement(self, eth_src, placement, static=False):
        """process device placement"""

    @abc.abstractmethod
    def process_device_behavior(self, eth_src, behavior, static=False):
        """process device behavior"""

    @abc.abstractmethod
    def get_vlan_from_segment(self, vlan):
        """get vlan from segment"""
