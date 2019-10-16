"""Various constants for use throuought forch"""

STATE_HEALTHY = 'healthy'  # All is good.
STATE_DAMAGED = 'damaged'  # Something is working ok, but not right.
STATE_DOWN = 'down'        # The system is down.
STATE_BROKEN = 'broken'    # Misconfiguration or other broken setup.

# TODO: Remove STATUS_ constants once all references have been removed.
STATUS_HEALTHY = 'healthy'
STATUS_DAMAGED = 'damaged'
STATUS_DOWN = 'down'
