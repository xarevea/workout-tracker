# ui/components/review_dialog.py
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QDoubleSpinBox
)
from PyQt6.QtCore import Qt

class WorkoutReviewDialog(QDialog):
    def __init__(self, session_logs, progression_suggestions, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Workout Review & Progression")
        self.resize(700, 400)
        self.session_logs = session_logs
        self.suggestions = progression_suggestions
        self.final_adjustments = {}

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        title = QLabel("Great job! Review your progressions for next time:")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        self.table = QTableWidget(len(self.suggestions), 4)
        self.table.setHorizontalHeaderLabels(["Exercise", "Performance", "Engine Suggestion", "Your Decision (Lbs)"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        for row, (exercise_name, data) in enumerate(self.suggestions.items()):
            # Exercise Name
            self.table.setItem(row, 0, QTableWidgetItem(exercise_name))
            
            # Performance Summary
            status = "Hit all targets" if data['target_met'] else "Missed targets"
            color = "#4CAF50" if data['target_met'] else "#F44336"
            item_status = QTableWidgetItem(status)
            item_status.setForeground(Qt.GlobalColor.white)
            item_status.setBackground(Qt.GlobalColor.darkGreen if data['target_met'] else Qt.GlobalColor.darkRed)
            self.table.setItem(row, 1, item_status)

            # Suggestion
            sugg_text = f"{data['action']}: {data['new_weight']} lbs"
            self.table.setItem(row, 2, QTableWidgetItem(sugg_text))

            # User Decision Spinbox
            spinbox = QDoubleSpinBox()
            spinbox.setRange(0, 1000)
            spinbox.setSingleStep(2.5)
            spinbox.setValue(data['new_weight'])
            self.table.setCellWidget(row, 3, spinbox)
            
            # Store reference to extract later
            self.final_adjustments[exercise_name] = spinbox

        layout.addWidget(self.table)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_approve = QPushButton("Approve & Save Workout")
        btn_approve.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; height: 30px;")
        btn_approve.clicked.connect(self.accept)
        
        btn_layout.addStretch()
        btn_layout.addWidget(btn_approve)
        layout.addLayout(btn_layout)

    def get_final_targets(self):
        """Returns the user's final approved weights for the next session."""
        results = {}
        for exercise, spinbox in self.final_adjustments.items():
            results[exercise] = spinbox.value()
        return results