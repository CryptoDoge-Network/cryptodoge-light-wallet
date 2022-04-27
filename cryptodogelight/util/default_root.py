import os
from pathlib import Path

DEFAULT_ROOT_PATH = Path(os.path.expanduser(os.getenv("CRYPTODOGE_ROOT", "~/.cryptodogelight/standalone_wallet"))).resolve()

DEFAULT_KEYS_ROOT_PATH = Path(os.path.expanduser(os.getenv("CRYPTODOGE_KEYS_ROOT", "~/.cryptodoge_keys"))).resolve()
