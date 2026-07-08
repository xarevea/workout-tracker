# ========================================
# FILE PATH: ui/views/equipment.py
# ========================================
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, 
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox, 
    QSpinBox, QDoubleSpinBox, QSplitter, QMessageBox
)
from PyQt6.QtCore import Qt
from core.db_operations import WorkoutDatabaseManager
from ui.views.base_view import BaseView
from core.events import event_bus

class EquipmentView(BaseView):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        
        title = QLabel("My Garage (Available Equipment)")
        title.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # --- LEFT PANEL: Add Equipment Form ---
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        left_layout.addWidget(QLabel("<b>Add New Equipment</b>"))
        
        self.eq_name = QLineEdit()
        self.eq_name.setPlaceholderText("Name (e.g., 45lb Bumper Plate)")
        left_layout.addWidget(QLabel("Equipment Name:"))
        left_layout.addWidget(self.eq_name)
        
        self.eq_weight = QDoubleSpinBox()
        self.eq_weight.setRange(0, 500)
        self.eq_weight.setSuffix(" lbs")
        left_layout.addWidget(QLabel("Weight:"))
        left_layout.addWidget(self.eq_weight)
        
        self.eq_qty = QSpinBox()
        self.eq_qty.setRange(1, 100)
        left_layout.addWidget(QLabel("Quantity:"))
        left_layout.addWidget(self.eq_qty)
        
        self.eq_is_barbell = QComboBox()
        self.eq_is_barbell.addItems(["Plate / Dumbbell (Single)", "Barbell / Machine (Base Weight)"])
        left_layout.addWidget(QLabel("Type:"))
        left_layout.addWidget(self.eq_is_barbell)
        
        btn_add = QPushButton("+ Add to Garage")
        btn_add.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; margin-top: 15px;")
        btn_add.clicked.connect(self._add_equipment)
        left_layout.addWidget(btn_add)
        
        splitter.addWidget(left_panel)

        # --- RIGHT PANEL: Equipment Inventory ---
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.addWidget(QLabel("<b>Current Inventory</b>"))
        
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Name", "Type", "Weight", "Qty", "Action"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        right_layout.addWidget(self.table)
        
        splitter.addWidget(right_panel)
        splitter.setSizes([300, 600])
        layout.addWidget(splitter)

    def refresh_data(self):
        self.table.setRowCount(0)
        equipment = WorkoutDatabaseManager.get_user_equipment(self.current_user_id)
        
        for row, item in enumerate(equipment):
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(item['name']))
            
            type_str = "Barbell" if item['is_barbell'] else "Plate/Dumbbell"
            self.table.setItem(row, 1, QTableWidgetItem(type_str))
            
            self.table.setItem(row, 2, QTableWidgetItem(f"{item['weight_lbs']} lbs"))
            self.table.setItem(row, 3, QTableWidgetItem(str(item['quantity'])))
            
            btn_del = QPushButton("Delete")
            btn_del.setStyleSheet("color: #F44336; background-color: transparent;")
            btn_del.clicked.connect(lambda _, e_id=item['id']: self._delete_equipment(e_id))
            self.table.setCellWidget(row, 4, btn_del)

    def _add_equipment(self):
        name = self.eq_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Error", "Equipment needs a name.")
            return
            
        is_bb = self.eq_is_barbell.currentIndex() == 1
        WorkoutDatabaseManager.add_equipment(self.current_user_id, name, self.eq_weight.value(), self.eq_qty.value(), is_bb)
        self.eq_name.clear()
        self.refresh_data()
        event_bus.data_changed.emit()

    def _delete_equipment(self, eq_id):
        WorkoutDatabaseManager.delete_equipment(eq_id)
        self.refresh_data()
        event_bus.data_changed.emit()