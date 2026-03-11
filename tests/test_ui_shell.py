import os

import pytest
from PySide6.QtCore import QTimer
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


def test_exit_action_quits_app(qapp) -> None:
    """Exit menu action quits the application, not just closes the window."""
    quit_emitted: list[bool] = []
    qapp.aboutToQuit.connect(lambda: quit_emitted.append(True))

    window = MainWindow()
    window.show()

    exit_action = next(
        action for action in window.findChildren(QAction) if action.text() == 'Exit'
    )
    QTimer.singleShot(0, exit_action.trigger)
    qapp.exec()

    assert quit_emitted == [True]
