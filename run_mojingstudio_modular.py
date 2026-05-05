from app.common import QApplication, sys
from app.main_window import SeedanceV5Workbench

if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = SeedanceV5Workbench()
    win.show()
    sys.exit(app.exec())
