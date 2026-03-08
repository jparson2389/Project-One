"""Pyside6 UI shell for main window implementation."""

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import (
    QLabel,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)


class MainWindow(QMainWindow):
    """Main window for the Aetherlink UI shell."""

    def __init__(self):
        """Initialize the main window and its UI components."""
        super().__init__()
        self.setWindowTitle("Aetherlink")
        self.setGeometry(100, 100, 800, 600)

        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # Add status bar
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Ready")

        # Add menu bar
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File")
        file_menu.addAction("Exit", lambda: QCoreApplication.instance().quit())

        # Add basic UI elements
        label = QLabel("Aetherlink UI Shell")
        layout.addWidget(label)
