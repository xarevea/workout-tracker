# ui/views/settings.py
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QGroupBox, QTableWidget, 
    QTableWidgetItem, QHeaderView, QComboBox, QMessageBox,
    QListWidget, QAbstractItemView
)
from core.database import get_connection

class SettingsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setSpacing(20)

        title = QLabel("Application Settings")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title)

        # --- FITBIT API SETTINGS (RESTORED) ---
        api_group = QGroupBox("Fitbit Auto-Sync Credentials")
        api_layout = QVBoxLayout()
        
        form_layout = QHBoxLayout()
        self.client_id_input = QLineEdit()
        self.client_id_input.setPlaceholderText("Enter Fitbit Client ID")
        self.client_secret_input = QLineEdit()
        self.client_secret_input.setPlaceholderText("Enter Fitbit Client Secret")
        self.client_secret_input.setEchoMode(QLineEdit.EchoMode.Password)
        
        form_layout.addWidget(QLabel("Client ID:"))
        form_layout.addWidget(self.client_id_input)
        form_layout.addWidget(QLabel("Secret:"))
        form_layout.addWidget(self.client_secret_input)
        
        self.btn_save_api = QPushButton("Save Credentials")
        self.btn_save_api.setFixedWidth(150)
        self.btn_save_api.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
        self.btn_save_api.clicked.connect(self._save_api_keys)
        
        api_layout.addLayout(form_layout)
        api_layout.addWidget(self.btn_save_api)
        api_group.setLayout(api_layout)
        layout.addWidget(api_group)

        # --- EXERCISE DICTIONARY EDITOR ---
        dict_group = QGroupBox("Exercise Dictionary Editor")
        dict_layout = QVBoxLayout()
        
        add_layout = QHBoxLayout()
        self.new_ex_name = QLineEdit()
        self.new_ex_name.setPlaceholderText("Exercise Name (e.g., Nordic Curls)")
        
        muscle_groups = ["Chest", "Back", "Quads", "Hamstrings", "Calves", "Shoulders", "Biceps", "Triceps", "Core", "Glutes"]
        
        self.new_ex_primary = QComboBox()
        self.new_ex_primary.addItems(muscle_groups)
        
        # Validated Multi-select List for Secondary Muscles
        self.new_ex_secondary = QListWidget()
        self.new_ex_secondary.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.new_ex_secondary.addItems(muscle_groups)
        self.new_ex_secondary.setFixedHeight(80) 
        
        self.btn_add_ex = QPushButton("+ Add to Database")
        self.btn_add_ex.setStyleSheet("background-color: #4CAF50; color: white; padding: 10px;")
        self.btn_add_ex.clicked.connect(self._add_exercise_to_db)
        
        add_layout.addWidget(self.new_ex_name)
        add_layout.addWidget(QLabel("Primary:"))
        add_layout.addWidget(self.new_ex_primary)
        add_layout.addWidget(QLabel("Secondary:"))
        add_layout.addWidget(self.new_ex_secondary)
        add_layout.addWidget(self.btn_add_ex)
        dict_layout.addLayout(add_layout)

        self.dict_table = QTableWidget(0, 3)
        self.dict_table.setHorizontalHeaderLabels(["Exercise Name", "Primary Muscle", "Secondary Muscles"])
        self.dict_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        dict_layout.addWidget(self.dict_table)
        
        self.btn_delete_ex = QPushButton("- Delete Selected Exercise")
        self.btn_delete_ex.setStyleSheet("background-color: #f44336; color: white;")
        self.btn_delete_ex.clicked.connect(self._delete_exercise)
        dict_layout.addWidget(self.btn_delete_ex)

        dict_group.setLayout(dict_layout)
        layout.addWidget(dict_group, stretch=1)

    def refresh_data(self):
        """Loads API keys and Exercise Dictionary from SQLite."""
        conn = get_connection()
        cursor = conn.cursor()
        
        # Load API Keys
        cursor.execute("SELECT access_token, refresh_token FROM api_integrations WHERE provider_name='Fitbit'")
        api_data = cursor.fetchone()
        if api_data:
            self.client_id_input.setText(api_data['access_token'])
            self.client_secret_input.setText(api_data['refresh_token'])

        # Load Exercises
        self.dict_table.setRowCount(0)
        cursor.execute("SELECT name, primary_muscle, secondary_muscles FROM exercises ORDER BY name ASC")
        for row, ex in enumerate(cursor.fetchall()):
            self.dict_table.insertRow(row)
            self.dict_table.setItem(row, 0, QTableWidgetItem(ex['name']))
            self.dict_table.setItem(row, 1, QTableWidgetItem(ex['primary_muscle'] or "N/A"))
            self.dict_table.setItem(row, 2, QTableWidgetItem(ex['secondary_muscles'] or "N/A"))
        conn.close()

    def _save_api_keys(self):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO api_integrations (id, provider_name, access_token, refresh_token) 
            VALUES (1, 'Fitbit', ?, ?)
            ON CONFLICT(id) DO UPDATE SET access_token=excluded.access_token, refresh_token=excluded.refresh_token
        ''', (self.client_id_input.text(), self.client_secret_input.text()))
        conn.commit()
        conn.close()
        QMessageBox.information(self, "Saved", "Fitbit credentials saved successfully.")

    def _add_exercise_to_db(self):
        name = self.new_ex_name.text().strip()
        if not name: return
        
        # Extract selected secondaries into a comma-separated string
        selected_secondaries = [item.text() for item in self.new_ex_secondary.selectedItems()]
        secondary_str = ", ".join(selected_secondaries)
        
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO exercises (name, category, primary_muscle, secondary_muscles)
                VALUES (?, 'Hybrid', ?, ?)
            ''', (name, self.new_ex_primary.currentText(), secondary_str))
            conn.commit()
            self.new_ex_name.clear()
            self.new_ex_secondary.clearSelection()
            self.refresh_data()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not add exercise. It may already exist.\n{e}")
        finally:
            conn.close()

    def _delete_exercise(self):
        current_row = self.dict_table.currentRow()
        if current_row < 0: return
        
        ex_name = self.dict_table.item(current_row, 0).text()
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM exercises WHERE name=?", (ex_name,))
        conn.commit()
        conn.close()
        self.refresh_data()