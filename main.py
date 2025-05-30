import sys

from gui.main_window import MainWindow
from PyQt6.QtWidgets import QApplication


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Cinema 4D Batch Renderer")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
