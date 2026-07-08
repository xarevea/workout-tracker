# ui/views/history.py
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, 
    QTableWidgetItem, QHeaderView, QPushButton, QMessageBox, QSplitter
)
from PyQt6.QtCore import Qt
from core.db_operations import WorkoutDatabaseManager
from ui.views.base_view import BaseView
from core.events import event_bus

class WorkoutHistoryView(BaseView):
    def __init__(self, parent=None):
        super().__init__(parent)
        event_bus.WORKOUT_COMPLETED.connect(self.refresh_data)
        
        layout = QHBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # --- LEFT: Workout List ---
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.addWidget(QLabel("<b>Past Workouts</b>"))
        
        self.workout_table = QTableWidget(0, 3)
        self.workout_table.setHorizontalHeaderLabels(["Date", "Workout", "Duration"])
        self.workout_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.workout_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.workout_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.workout_table.itemSelectionChanged.connect(self._on_workout_selected)
        left_layout.addWidget(self.workout_table)
        
        btn_delete_workout = QPushButton("🗑️ Delete Selected Workout")
        btn_delete_workout.setStyleSheet("color: #F44336;")
        btn_delete_workout.clicked.connect(self._delete_selected_workout)
        left_layout.addWidget(btn_delete_workout)
        
        splitter.addWidget(left_panel)
        
        # --- RIGHT: Workout Logs ---
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        self.lbl_details = QLabel("<b>Workout Details</b>")
        right_layout.addWidget(self.lbl_details)
        
        self.log_table = QTableWidget(0, 5)
        self.log_table.setHorizontalHeaderLabels(["Exercise", "Set", "Reps", "Weight", "RPE"])
        self.log_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        right_layout.addWidget(self.log_table)
        
        splitter.addWidget(right_panel)
        splitter.setSizes([400, 600])
        layout.addWidget(splitter)

    def refresh_data(self):
        self.workout_table.blockSignals(True)
        self.workout_table.setRowCount(0)
        
        workouts = WorkoutDatabaseManager.get_workout_history(self.current_user_id)
        for i, w in enumerate(workouts):
            self.workout_table.insertRow(i)
            self.workout_table.setItem(i, 0, QTableWidgetItem(w['date'].split(" ")[0]))
            self.workout_table.setItem(i, 1, QTableWidgetItem(w['name']))
            self.workout_table.setItem(i, 2, QTableWidgetItem(f"{w['duration_minutes']} min"))
            
            # Store ID invisibly
            self.workout_table.item(i, 0).setData(Qt.ItemDataRole.UserRole, w['id'])
            
        self.workout_table.blockSignals(False)
        self.log_table.setRowCount(0)

    def _on_workout_selected(self):
        row = self.workout_table.currentRow()
        if row < 0: return
        
        workout_id = self.workout_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        name = self.workout_table.item(row, 1).text()
        self.lbl_details.setText(f"<b>Details for: {name}</b>")
        
        logs = WorkoutDatabaseManager.get_workout_logs(workout_id)
        self.log_table.setRowCount(0)
        
        for i, log in enumerate(logs):
            self.log_table.insertRow(i)
            self.log_table.setItem(i, 0, QTableWidgetItem(log['exercise']))
            self.log_table.setItem(i, 1, QTableWidgetItem("W" if log['is_warmup'] else str(log['set_number'])))
            self.log_table.setItem(i, 2, QTableWidgetItem(str(log['reps'])))
            self.log_table.setItem(i, 3, QTableWidgetItem(f"{log['weight_lbs']} lbs"))
            self.log_table.setItem(i, 4, QTableWidgetItem(str(log['rpe'])))

    def _delete_selected_workout(self):
        row = self.workout_table.currentRow()
        if row < 0: return
        
        workout_id = self.workout_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        confirm = QMessageBox.question(self, "Confirm Delete", "Are you sure you want to permanently delete this workout and all its sets?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if confirm == QMessageBox.StandardButton.Yes:
            WorkoutDatabaseManager.delete_workout(workout_id)
            self.refresh_data()