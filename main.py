from .common import *
from .main_window import SeedanceV5Workbench

def run():
    ensure_data_dirs()
    app = QApplication(sys.argv)
    win = SeedanceV5Workbench()
    win.show()
    return app.exec()

if __name__ == "__main__":
    sys.exit(run())
