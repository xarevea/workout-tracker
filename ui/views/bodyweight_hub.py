# ui/views/bodyweight_hub.py
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QDoubleSpinBox, 
    QCalendarWidget, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView
)
from core.db_operations import WorkoutDatabaseManager

class BodyweightHubView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        
        # --- LEFT: Logger ---
        left = QVBoxLayout()
        title = QLabel("Bodyweight Hub")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        left.addWidget(title)
        
        self.calendar = QCalendarWidget()
        self.calendar.setStyleSheet("background-color: #2d2d2d; color: white;")
        left.addWidget(self.calendar)
        
        input_layout = QHBoxLayout()
        self.spin_weight = QDoubleSpinBox()
        self.spin_weight.setRange(50, 500)
        self.spin_weight.setValue(180.0)
        self.spin_weight.setSuffix(" lbs")
        self.spin_weight.setStyleSheet("font-size: 18px; padding: 5px;")
        
        self.btn_log = QPushButton("Log Morning Weight")
        self.btn_log.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold; padding: 5px;")
        self.btn_log.clicked.connect(self._log_weight)
        
        input_layout.addWidget(self.spin_weight)
        input_layout.addWidget(self.btn_log)
        left.addLayout(input_layout)
        left.addStretch()
        layout.addLayout(left, stretch=1)
        
        # --- RIGHT: History ---
        right = QVBoxLayout()
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Date Recorded", "Morning Weight (lbs)"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        
        right.addWidget(self.table)
        layout.addLayout(right, stretch=1)
        
        self.refresh_data()

    def _show_context_menu(self, pos):
        from PyQt6.QtWidgets import QMenu
        menu = QMenu()
        delete_action = menu.addAction("Delete Entry")
        action = menu.exec(self.table.viewport().mapToGlobal(pos))
        
        if action == delete_action:
            row = self.table.rowAt(pos.y())
            if row >= 0:
                date_str = self.table.item(row, 0).text()
                # You'll need to add delete_bodyweight_log(date_str) to db_operations
                WorkoutDatabaseManager.delete_bodyweight_log(date_str)
                self.refresh_data()

    def refresh_data(self):
        self.table.setRowCount(0)
        logs = WorkoutDatabaseManager.get_bodyweight_history()
        for i, log in enumerate(reversed(logs)): # Show newest first
            self.table.insertRow(i)
            self.table.setItem(i, 0, QTableWidgetItem(log['date']))
            self.table.setItem(i, 1, QTableWidgetItem(str(log['weight_lbs'])))
            
    def _log_weight(self):
        date_str = self.calendar.selectedDate().toString("yyyy-MM-dd")
        WorkoutDatabaseManager.log_bodyweight(date_str, self.spin_weight.value())
        self.refresh_data()