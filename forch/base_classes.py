"""Collection of abstract base classes used elsewhere"""

import abc


class OrchestrationManager(abc.ABC):
    """Interface collecting the methods that manage orchestration"""

    @abc.abstractmethod
    def reregister_include_file_watchers(self, old_include_files, new_include_files):
        """reregister the include file watchers"""

    @abc.abstractmethod
    def reset_faucet_config_writing_time(self):
        """reset config writing time"""


class DeviceStateReporter(abc.ABC):
    """Interface reporting device information"""

    @abc.abstractmethod
    def disconnect(self, mac):
        """Disconnect a device for reporting"""

    @abc.abstractmethod
    def process_port_state(self, dp_name, port, state):
        """Process faucet port state events"""

    @abc.abstractmethod
    def process_port_learn(self, dp_name, port, mac, vlan):
        """Process faucet port learn events"""

    @abc.abstractmethod
    def process_port_assign(self, mac, vlan):
        """Process faucet port vlan assignment"""
