from __future__ import annotations

import os
import shutil
from pathlib import Path

from loguru import logger


def _cleanup_stubs(stub_dir):
    for item in os.listdir(stub_dir):
        item_path = os.path.join(stub_dir, item)
        if os.path.isfile(item_path) or os.path.islink(item_path):
            try:
                os.unlink(item_path)
            except Exception as e:
                logger.error(f'Failed to delete {item_path}: {e}')
        elif os.path.isdir(item_path):
            shutil.rmtree(item_path)


if __name__ == '__main__':
    stub_dir = Path('src/aetherlink/plugins/capture/_stubs/')
    _cleanup_stubs(stub_dir)
