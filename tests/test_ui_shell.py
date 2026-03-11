import os

import pytest
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QMainWindow
from src.aetherlink.ui.main_window import MainWindow

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')


@pytest.fixture(scope='module')
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_main_window_instantiation(qapp) -> None:
    window = MainWindow()
    assert isinstance(window, QMainWindow)
    assert window.windowTitle() == 'Aetherlink'


def test_status_bar_visible(qapp) -> None:
    window = MainWindow()
    assert window.statusBar() is not None


def test_exit_action_closes_window(qapp) -> None:
    window = MainWindow()
    window.show()

    exit_action = next(
        action for action in window.findChildren(QAction) if action.text() == 'Exit'
    )
    assert exit_action.text() == 'Exit'
    assert window.isVisible()

    exit_action.trigger()
    qapp.processEvents()

    assert not window.isVisible()
