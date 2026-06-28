# ui/views/program_builder.py
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox, QCheckBox, QSpinBox, QMessageBox, QDialog
)
from core.db_operations import WorkoutDatabaseManager
from ui.components.body_heatmap import AnatomicalHeatmap

class ProgramAnalysisDialog(QDialog):
    def __init__(self, program_name, volume_map, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Program Analysis: {program_name}")
        self.resize(600, 500)
        layout = QVBoxLayout(self)
        
        title = QLabel("Full Program Muscular Balance Overlay")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)
        
        heatmap = AnatomicalHeatmap()
        heatmap.update_heatmap(volume_map)
        layout.addWidget(heatmap)

class ProgramBuilderView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        
        title = QLabel("Periodization & Program Builder")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        self.layout.addWidget(title)
        
        top = QHBoxLayout()
        self.program_name = QLineEdit()
        self.program_name.setPlaceholderText("Program Name (e.g., 8-Week Hybrid)")
        
        self.cycle_days = QSpinBox()
        self.cycle_days.setPrefix("Cycle Length (Days): ")
        self.cycle_days.setRange(1, 30)
        self.cycle_days.setValue(7)
        self.cycle_days.valueChanged.connect(self._rebuild_table)
        
        btn_save = QPushButton("Save Program")
        btn_save.setStyleSheet("background-color: #4CAF50; color: white;")
        btn_save.clicked.connect(self._save_program)
        
        btn_analyze = QPushButton("Analyze Full Program Balance")
        btn_analyze.setStyleSheet("background-color: #9C27B0; color: white;")
        btn_analyze.clicked.connect(self._analyze_program)
        
        top.addWidget(self.program_name)
        top.addWidget(self.cycle_days)
        top.addWidget(btn_save)
        top.addWidget(btn_analyze)
        self.layout.addLayout(top)
        
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Day #", "Routine Template", "Periodization Flag"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.layout.addWidget(self.table)
        
    def refresh_data(self):
        self.templates = WorkoutDatabaseManager.get_all_templates()
        self._rebuild_table()
        
    def _rebuild_table(self):
        days = self.cycle_days.value()
        self.table.setRowCount(days)
        for i in range(days):
            self.table.setItem(i, 0, QTableWidgetItem(f"Day {i+1}"))
            
            combo = QComboBox()
            combo.addItem("Rest Day", userData=None)
            for t in self.templates:
                combo.addItem(t['name'], userData=t['id'])
            self.table.setCellWidget(i, 1, combo)
            
            chk = QCheckBox("Mark as Deload Day (Reduces Load via Engine)")
            self.table.setCellWidget(i, 2, chk)

    def _save_program(self):
        name = self.program_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Error", "Program must have a name.")
            return
            
        days_data = []
        for i in range(self.table.rowCount()):
            t_id = self.table.cellWidget(i, 1).currentData()
            is_deload = 1 if self.table.cellWidget(i, 2).isChecked() else 0
            if t_id:
                days_data.append({"day_number": i+1, "template_id": t_id, "is_deload": is_deload})
                
        WorkoutDatabaseManager.save_program(name, self.cycle_days.value(), days_data)
        QMessageBox.information(self, "Saved", f"Program '{name}' saved successfully.")

    def _analyze_program(self):
        name = self.program_name.text().strip()
        if not name: return
        v_map = WorkoutDatabaseManager.get_program_volume_map(name)
        dialog = ProgramAnalysisDialog(name, v_map, self)
        dialog.exec()