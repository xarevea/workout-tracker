# main.py
import sys
import argparse
import os
import atexit
from PyQt6.QtWidgets import QApplication
from utils.theme_manager import apply_theme
import qdarktheme

import core.database
from core.database import initialize_database
from ui.main_window import MainWindow

def main():
    # 1. Parse Command Line Arguments
    parser = argparse.ArgumentParser(description="Hybrid Tracker App")
    parser.add_argument('--test', action='store_true', help="Seed the database with mock historical data")
    args = parser.parse_args()

    if args.test:
        test_db_path = os.path.abspath('test_tracker.db')

        def cleanup_test_db():
            import gc
            gc.collect() # Force close dangling SQLite handles
            if os.path.exists(test_db_path):
                try:
                    os.remove(test_db_path)
                    print("Test database cleaned up.")
                except Exception as e:
                    pass

        cleanup_test_db() # Clear leftover test DB before start

        core.database.set_database_path(test_db_path)
        atexit.register(cleanup_test_db)
        print(f"Running in TEST mode. Isolated DB: {test_db_path}")

    # 2. Initialize Database
    initialize_database()

    if args.test:
        from utils.mock_data import seed_database
        print("Test flag detected: Seeding mock historical database...")
        seed_database()

    # 3. Boot UI
    app = QApplication(sys.argv)
    qdarktheme.setup_theme(
        theme="dark",
        corner_shape="sharp",
        custom_colors={"primary": "#4CAF50"}
    )

    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()