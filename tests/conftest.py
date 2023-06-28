import os
from pathlib import Path


def get_dir(file: str) -> Path:
    """Return parent directory of `file`."""
    return Path(os.path.realpath(file)).parent
