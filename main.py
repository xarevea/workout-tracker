# main.py
import sys
import argparse
import os
import tempfile
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
        test_db_fd, test_db_path = tempfile.mkstemp(suffix='.db', prefix='workout_test_')
        os.close(test_db_fd)
        core.database.DB_PATH = test_db_path  # Override the DB path before initialization
        
        def cleanup_test_db():
            if os.path.exists(test_db_path):
                try:
                    os.remove(test_db_path)
                    print("Test database cleaned up.")
                except Exception as e:
                    pass
        
        atexit.register(cleanup_test_db)
        print(f"Running in TEST mode. Isolated DB: {test_db_path}")

    # 2. Initialize Database
    initialize_database()

    if args.test:
        from utils.mock_data import seed_database
        print("Test flag detected: Seeding mock historical database...")
        seed_database()

    # 4. Boot UI
    app = QApplication(sys.argv)
    # apply_theme(app, theme_name="catppuccin")
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