from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, 
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox, 
    QMessageBox, QListWidget, QAbstractItemView, QTabWidget, QSpinBox, QDoubleSpinBox
)
from core.database import get_connection
from ui.views.base_view import BaseView

class SettingsView(BaseView):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        
        title = QLabel("Application Settings")
        title.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self._setup_api_tab()
        self._setup_dict_tab()
        self._setup_garage_tab()
        self.refresh_data()

    def refresh_data(self):
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT access_token, refresh_token FROM api_integrations WHERE provider_name='Fitbit'")
        api_data = cursor.fetchone()
        if api_data:
            self.client_id_input.setText(api_data['access_token'])
            self.client_secret_input.setText(api_data['refresh_token'])

        self.dict_table.setRowCount(0)
        cursor.execute("SELECT name, primary_muscle, secondary_muscles FROM exercises ORDER BY name ASC")
        for row, ex in enumerate(cursor.fetchall()):
            self.dict_table.insertRow(row)
            self.dict_table.setItem(row, 0, QTableWidgetItem(ex['name']))
            self.dict_table.setItem(row, 1, QTableWidgetItem(ex['primary_muscle'] or "N/A"))
            self.dict_table.setItem(row, 2, QTableWidgetItem(ex['secondary_muscles'] or "N/A"))
            
        self.garage_table.setRowCount(0)
        cursor.execute("SELECT name, weight_lbs, quantity, is_barbell FROM equipment ORDER BY weight_lbs DESC")
        for row, item in enumerate(cursor.fetchall()):
            self.garage_table.insertRow(row)
            self.garage_table.setItem(row, 0, QTableWidgetItem(item['name']))
            self.garage_table.setItem(row, 1, QTableWidgetItem(f"{item['weight_lbs']} lbs"))
            self.garage_table.setItem(row, 2, QTableWidgetItem(str(item['quantity'])))
            self.garage_table.setItem(row, 3, QTableWidgetItem("Yes" if item['is_barbell'] else "No"))
        conn.close()

    def _setup_api_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        form_layout = QHBoxLayout()
        self.client_id_input = QLineEdit()
        self.client_secret_input = QLineEdit()
        self.client_secret_input.setEchoMode(QLineEdit.EchoMode.Password)
        
        form_layout.addWidget(QLabel("Client ID:"))
        form_layout.addWidget(self.client_id_input)
        form_layout.addWidget(QLabel("Secret:"))
        form_layout.addWidget(self.client_secret_input)
        
        btn_save = QPushButton("Save Credentials")
        btn_save.setStyleSheet("background-color: #2196F3; color: white;")
        btn_save.clicked.connect(self._save_api_keys)
        
        layout.addLayout(form_layout)
        layout.addWidget(btn_save)
        layout.addStretch()
        self.tabs.addTab(tab, "Fitbit API")

    def _setup_dict_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        add_layout = QHBoxLayout()
        
        self.new_ex_name = QLineEdit()
        muscle_groups = ["Chest", "Back", "Quads", "Hamstrings", "Calves", "Shoulders", "Biceps", "Triceps", "Core", "Glutes"]
        self.new_ex_primary = QComboBox()
        self.new_ex_primary.addItems(muscle_groups)
        self.new_ex_secondary = QListWidget()
        self.new_ex_secondary.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.new_ex_secondary.addItems(muscle_groups)
        self.new_ex_secondary.setFixedHeight(80) 
        
        btn_add = QPushButton("+ Add")
        btn_add.clicked.connect(self._add_exercise_to_db)
        
        add_layout.addWidget(self.new_ex_name)
        add_layout.addWidget(self.new_ex_primary)
        add_layout.addWidget(self.new_ex_secondary)
        add_layout.addWidget(btn_add)
        layout.addLayout(add_layout)

        self.dict_table = QTableWidget(0, 3)
        self.dict_table.setHorizontalHeaderLabels(["Name", "Primary", "Secondary"])
        self.dict_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.dict_table)
        self.tabs.addTab(tab, "Exercise Dictionary")

    def _setup_garage_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        add_layout = QHBoxLayout()
        self.eq_name = QLineEdit()
        self.eq_name.setPlaceholderText("Name (e.g., 45lb Plate)")
        self.eq_weight = QDoubleSpinBox()
        self.eq_weight.setSuffix(" lbs")
        self.eq_qty = QSpinBox()
        self.eq_qty.setPrefix("Qty: ")
        self.eq_is_barbell = QComboBox()
        self.eq_is_barbell.addItems(["Plate/Dumbbell", "Barbell"])
        
        btn_add = QPushButton("+ Add Equipment")
        btn_add.clicked.connect(self._add_equipment_to_db)
        
        add_layout.addWidget(self.eq_name)
        add_layout.addWidget(self.eq_weight)
        add_layout.addWidget(self.eq_qty)
        add_layout.addWidget(self.eq_is_barbell)
        add_layout.addWidget(btn_add)
        layout.addLayout(add_layout)
        
        self.garage_table = QTableWidget(0, 4)
        self.garage_table.setHorizontalHeaderLabels(["Name", "Weight", "Quantity", "Is Barbell?"])
        self.garage_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.garage_table)
        self.tabs.addTab(tab, "My Garage")

    def _save_api_keys(self):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO api_integrations (id, provider_name, access_token, refresh_token) VALUES (1, 'Fitbit', ?, ?) ON CONFLICT(id) DO UPDATE SET access_token=excluded.access_token, refresh_token=excluded.refresh_token", (self.client_id_input.text(), self.client_secret_input.text()))
        conn.commit(); conn.close()

    def _add_exercise_to_db(self):
        name = self.new_ex_name.text().strip()
        secondaries = ", ".join([item.text() for item in self.new_ex_secondary.selectedItems()])
        conn = get_connection(); cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO exercises (name, category, primary_muscle, secondary_muscles) VALUES (?, 'Hybrid', ?, ?)", (name, self.new_ex_primary.currentText(), secondaries))
        conn.commit(); conn.close(); self.refresh_data()

    def _add_equipment_to_db(self):
        name = self.eq_name.text().strip()
        is_bb = 1 if self.eq_is_barbell.currentText() == "Barbell" else 0
        conn = get_connection(); cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO equipment (name, weight_lbs, quantity, is_barbell) VALUES (?, ?, ?, ?)", (name, self.eq_weight.value(), self.eq_qty.value(), is_bb))
        conn.commit(); conn.close(); self.refresh_data()