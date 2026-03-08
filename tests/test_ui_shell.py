import os

import pytest
from PySide6.QtWidgets import QApplication, QMainWindow
from src.aetherlink.ui.main_window import MainWindow

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_main_window_instantiation(qapp) -> None:
    window = MainWindow()
    assert isinstance(window, QMainWindow)
    assert window.windowTitle() == "Aetherlink"


def test_status_bar_visible(qapp) -> None:
    window = MainWindow()
    assert window.statusBar() is not None
