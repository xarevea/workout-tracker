# ui/components/review_dialog.py
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget, 
    QTableWidgetItem, QHeaderView, QDoubleSpinBox, QSpinBox, QWidget
)
from PyQt6.QtCore import Qt

class WorkoutReviewDialog(QDialog):
    def __init__(self, session_logs, progression_suggestions, current_settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Workout Review & Progression")
        self.resize(900, 400)
        self.suggestions = progression_suggestions
        self.current_settings = current_settings
        self.final_adjustments = {}
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        self.table = QTableWidget(len(self.suggestions), 4)
        self.table.setHorizontalHeaderLabels(["Exercise", "Current Target", "Engine Suggestion", "Final Decision"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        for row, (exercise_name, data) in enumerate(self.suggestions.items()):
            self.table.setItem(row, 0, QTableWidgetItem(exercise_name))
            
            curr = self.current_settings.get(exercise_name, {})
            curr_str = f"{curr.get('weight', 0)} lbs @ {curr.get('min_reps', 0)}-{curr.get('max_reps', 0)} reps"
            self.table.setItem(row, 1, QTableWidgetItem(curr_str))

            sugg_text = f"{data['action']}: {data['new_weight']} lbs @ {data['new_min']}-{data['new_max']} reps"
            sugg_item = QTableWidgetItem(sugg_text)
            if "INCREASE" in data['action']:
                sugg_item.setBackground(Qt.GlobalColor.darkGreen)
                sugg_item.setForeground(Qt.GlobalColor.white)
            self.table.setItem(row, 2, sugg_item)

            dec_widget = QWidget()
            dec_layout = QHBoxLayout(dec_widget)
            dec_layout.setContentsMargins(0,0,0,0)
            
            spin_wt = QDoubleSpinBox()
            spin_wt.setRange(0, 1500)
            spin_wt.setValue(data['new_weight'])
            
            spin_min = QSpinBox()
            spin_min.setValue(data['new_min'])
            
            spin_max = QSpinBox()
            spin_max.setValue(data['new_max'])
            
            dec_layout.addWidget(spin_wt)
            dec_layout.addWidget(QLabel("lbs @"))
            dec_layout.addWidget(spin_min)
            dec_layout.addWidget(QLabel("-"))
            dec_layout.addWidget(spin_max)
            
            self.table.setCellWidget(row, 3, dec_widget)
            self.final_adjustments[exercise_name] = {'weight': spin_wt, 'min_reps': spin_min, 'max_reps': spin_max}

        layout.addWidget(self.table)
        btn_approve = QPushButton("Approve & Update Routine")
        btn_approve.setStyleSheet("background-color: #4CAF50; color: white; height: 30px;")
        btn_approve.clicked.connect(self.accept)
        layout.addWidget(btn_approve)

    def get_final_targets(self):
        results = {}
        for exercise, widgets in self.final_adjustments.items():
            results[exercise] = {
                'weight': widgets['weight'].value(),
                'min_reps': widgets['min_reps'].value(),
                'max_reps': widgets['max_reps'].value()
            }
        return results