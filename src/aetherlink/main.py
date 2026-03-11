"""Aetherlink CLI entrypoint."""

import sys

from loguru import logger
from PySide6.QtWidgets import QApplication

from aetherlink.ui.main_window import MainWindow


def main() -> None:
    """Run the Aetherlink CLI entrypoint."""
    logger.info('Aetherlink CLI started.')
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
