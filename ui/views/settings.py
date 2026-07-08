# ========================================
# FILE PATH: ui/views/settings.py
# ========================================
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, 
    QTabWidget, QMessageBox
)
from core.db_operations import WorkoutDatabaseManager
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
        self._setup_data_tab() 
        self.refresh_data()

    def refresh_data(self):
        api_data = WorkoutDatabaseManager.get_api_credentials("Fitbit")
        if api_data:
            self.client_id_input.setText(api_data['access_token'])
            self.client_secret_input.setText(api_data['refresh_token'])

    def _setup_api_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        info = QLabel("<b>Fitbit Health Wearable Integration</b><br>Sync your daily readiness, heart rate, and sleep score to overlay with your strength progression data.")
        layout.addWidget(info)
        
        form_layout = QHBoxLayout()
        self.client_id_input = QLineEdit()
        self.client_secret_input = QLineEdit()
        self.client_secret_input.setEchoMode(QLineEdit.EchoMode.Password)
        
        form_layout.addWidget(QLabel("Client ID:"))
        form_layout.addWidget(self.client_id_input)
        form_layout.addWidget(QLabel("Secret:"))
        form_layout.addWidget(self.client_secret_input)
        layout.addLayout(form_layout)
        
        btn_save = QPushButton("Save Credentials")
        btn_save.setStyleSheet("background-color: #2196F3; color: white;")
        btn_save.clicked.connect(self._save_api_keys)
        layout.addWidget(btn_save)
        
        layout.addStretch()
        self.tabs.addTab(tab, "Integrations")

    def _setup_data_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        info = QLabel("<b>Data Management</b><br>Backup or export your entire workout history.")
        layout.addWidget(info)
        
        btn_export = QPushButton("Export Database to CSV (Coming Soon)")
        btn_export.setEnabled(False)
        layout.addWidget(btn_export)
        
        layout.addStretch()
        self.tabs.addTab(tab, "Data Management")

    def _save_api_keys(self):
        WorkoutDatabaseManager.save_api_credentials("Fitbit", self.client_id_input.text(), self.client_secret_input.text())
        QMessageBox.information(self, "Saved", "API Credentials saved successfully.")