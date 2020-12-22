"""Varz updating interface"""

import abc


class VarzUpdater(abc.ABC):
    """An interface collecting the methods to update forch varz"""

    def update_device_state_varz(self, mac, state):
        pass

    def update_static_vlan_varz(self, mac, vlan):
        pass
