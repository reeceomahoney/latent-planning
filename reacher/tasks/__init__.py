import os
import toml

from omni.isaac.lab_tasks.utils import import_packages
from .reacher_rl.config import *

##
# Register Gym environments.
##


# The blacklist is used to prevent importing configs from sub-packages
_BLACKLIST_PKGS = ["utils"]
# Import all configs in this package
import_packages(__name__, _BLACKLIST_PKGS)
