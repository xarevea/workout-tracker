# main.py
import sys
import argparse
from PyQt6.QtWidgets import QApplication
import qdarktheme

from core.database import initialize_database
from ui.main_window import MainWindow

def main():
    # 1. Parse Command Line Arguments
    parser = argparse.ArgumentParser(description="Hybrid Tracker App")
    parser.add_argument('--test', action='store_true', help="Seed the database with mock historical data")
    args = parser.parse_args()

    # 2. Initialize Database
    initialize_database()

    # 3. Seed Data if --test is used
    if args.test:
        from utils.mock_data import generate_test_data
        print("Test flag detected: Seeding mock historical database...")
        generate_test_data()

    # 4. Boot UI
    app = QApplication(sys.argv)
    qdarktheme.setup_theme(theme="dark", custom_colors={"primary": "#4CAF50"})

    window = MainWindow()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()