from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QPushButton, QMessageBox, QSplitter,
    QDialog, QLineEdit, QDateEdit, QSpinBox, QComboBox, QDoubleSpinBox
)
from PyQt6.QtCore import Qt, QDate, QThreadPool
from PyQt6.QtGui import QColor

from core.db_operations import WorkoutDatabaseManager
from core.events import event_bus
from ui.views.base_view import BaseView
from utils.threads import Worker

class ManualWorkoutEntryDialog(QDialog):
    def __init__(self, user_id, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.setWindowTitle("Log Past Workout")
        self.resize(850, 500)
        layout = QVBoxLayout(self)

        header = QHBoxLayout()
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())

        self.txt_name = QLineEdit()
        self.txt_name.setPlaceholderText("Workout Name (e.g. Pull Day)")

        self.spin_dur = QSpinBox(); self.spin_dur.setSuffix(" min"); self.spin_dur.setValue(60)
        self.spin_bw = QDoubleSpinBox(); self.spin_bw.setSuffix(" lbs"); self.spin_bw.setRange(50, 500)
        self.spin_bw.setValue(WorkoutDatabaseManager.get_latest_bodyweight(user_id))

        header.addWidget(QLabel("Date:")); header.addWidget(self.date_edit)
        header.addWidget(self.txt_name)
        header.addWidget(QLabel("Duration:")); header.addWidget(self.spin_dur)
        header.addWidget(QLabel("Bodyweight:")); header.addWidget(self.spin_bw)
        layout.addLayout(header)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["Exercise", "Set", "Reps", "Weight", "RPE", "Notes", ""])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)

        controls = QHBoxLayout()
        btn_add_row = QPushButton("+ Add Set")
        btn_add_row.clicked.connect(self._add_row)
        btn_save = QPushButton("Save History")
        btn_save.setStyleSheet("background-color: #4CAF50; color: white;")
        btn_save.clicked.connect(self._save)

        controls.addWidget(btn_add_row)
        controls.addStretch()
        controls.addWidget(btn_save)
        layout.addLayout(controls)

        self.exercise_bank = [ex['name'] for ex in WorkoutDatabaseManager.get_all_exercises()]
        self._add_row()

    def _add_row(self):
        row = self.table.rowCount()
        self.table.insertRow(row)

        combo_ex = QComboBox(); combo_ex.addItems(self.exercise_bank); combo_ex.setEditable(True)
        spin_set = QSpinBox(); spin_set.setValue(1)
        spin_reps = QSpinBox(); spin_reps.setValue(10)
        spin_wt = QDoubleSpinBox(); spin_wt.setRange(0, 1500)
        spin_rpe = QDoubleSpinBox(); spin_rpe.setRange(1, 10); spin_rpe.setValue(8)
        txt_notes = QLineEdit()

        btn_del = QPushButton("X"); btn_del.setStyleSheet("color: red;")
        btn_del.clicked.connect(lambda checked, b=btn_del: self.table.removeRow(
            next((i for i in range(self.table.rowCount()) if self.table.cellWidget(i, 6) == b), -1)
        ))

        self.table.setCellWidget(row, 0, combo_ex)
        self.table.setCellWidget(row, 1, spin_set)
        self.table.setCellWidget(row, 2, spin_reps)
        self.table.setCellWidget(row, 3, spin_wt)
        self.table.setCellWidget(row, 4, spin_rpe)
        self.table.setCellWidget(row, 5, txt_notes)
        self.table.setCellWidget(row, 6, btn_del)

    def _save(self):
        if not self.txt_name.text().strip():
            QMessageBox.warning(self, "Error", "Name is required.")
            return

        logs = []
        for i in range(self.table.rowCount()):
            logs.append({
                "exercise": self.table.cellWidget(i, 0).currentText(),
                "set": self.table.cellWidget(i, 1).value(),
                "reps": self.table.cellWidget(i, 2).value(),
                "weight": self.table.cellWidget(i, 3).value(),
                "rpe": self.table.cellWidget(i, 4).value(),
                "is_warmup": False,
                "notes": self.table.cellWidget(i, 5).text().strip()
            })

        date_str = self.date_edit.date().toString("yyyy-MM-dd") + " 12:00:00"

        WorkoutDatabaseManager.save_completed_workout(
            user_id=self.user_id,
            workout_name=self.txt_name.text(),
            duration_minutes=self.spin_dur.value(),
            bodyweight=self.spin_bw.value(),
            logs=logs,
            date_str=date_str
        )
        self.accept()

class WorkoutHistoryView(BaseView):
    def __init__(self, parent=None):
        super().__init__(parent)
        event_bus.WORKOUT_COMPLETED.connect(self.refresh_data)

        layout = QHBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)

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

        btn_layout = QHBoxLayout()
        btn_add_manual = QPushButton("➕ Add Past Workout")
        btn_add_manual.setStyleSheet("color: #4CAF50; font-weight: bold;")
        btn_add_manual.clicked.connect(self._add_manual_workout)

        btn_delete_workout = QPushButton("🗑️ Delete Selected Workout")
        btn_delete_workout.setStyleSheet("color: #F44336;")
        btn_delete_workout.clicked.connect(self._delete_selected_workout)

        btn_layout.addWidget(btn_add_manual)
        btn_layout.addWidget(btn_delete_workout)
        left_layout.addLayout(btn_layout)

        splitter.addWidget(left_panel)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        self.lbl_details = QLabel("<b>Workout Details</b>")
        right_layout.addWidget(self.lbl_details)

        self.log_table = QTableWidget(0, 6)
        self.log_table.setHorizontalHeaderLabels(["Exercise", "Set", "Reps", "Weight", "RPE", "Notes"])
        self.log_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        right_layout.addWidget(self.log_table)

        splitter.addWidget(right_panel)
        splitter.setSizes([400, 600])
        layout.addWidget(splitter)

    def refresh_data(self):
        self.workout_table.blockSignals(True)
        self.workout_table.setRowCount(0)
        self.log_table.setRowCount(0)
        self.lbl_details.setText("<b>Loading Workout History...</b>")

        worker = Worker(self._fetch_history)
        worker.signals.result.connect(self._render_history)
        QThreadPool.globalInstance().start(worker)

    def _fetch_history(self):
        return WorkoutDatabaseManager.get_workout_history(self.current_user_id)

    def _render_history(self, workouts):
        for i, w in enumerate(workouts):
            self.workout_table.insertRow(i)
            self.workout_table.setItem(i, 0, QTableWidgetItem(w['date'].split(" ")[0]))
            self.workout_table.setItem(i, 1, QTableWidgetItem(w['name']))
            self.workout_table.setItem(i, 2, QTableWidgetItem(f"{w['duration_minutes']} min"))
            self.workout_table.item(i, 0).setData(Qt.ItemDataRole.UserRole, w['id'])

        self.workout_table.blockSignals(False)
        self.lbl_details.setText("<b>Select a workout to view details</b>")

    def _on_workout_selected(self):
        row = self.workout_table.currentRow()
        if row < 0: return

        workout_id = self.workout_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        name = self.workout_table.item(row, 1).text()

        self.lbl_details.setText(f"<b>Loading Details for: {name}...</b>")
        self.log_table.setRowCount(0)

        worker = Worker(WorkoutDatabaseManager.get_workout_logs, workout_id)
        worker.signals.result.connect(lambda logs, n=name: self._render_logs(logs, n))
        QThreadPool.globalInstance().start(worker)

    def _render_logs(self, logs, name):
        self.lbl_details.setText(f"<b>Details for: {name}</b>")
        for i, log in enumerate(logs):
            self.log_table.insertRow(i)
            self.log_table.setItem(i, 0, QTableWidgetItem(log['exercise']))
            self.log_table.setItem(i, 1, QTableWidgetItem("W" if log['is_warmup'] else str(log['set_number'])))
            self.log_table.setItem(i, 2, QTableWidgetItem(str(log['reps'])))
            self.log_table.setItem(i, 3, QTableWidgetItem(f"{log['weight_lbs']} lbs"))
            self.log_table.setItem(i, 4, QTableWidgetItem(str(log['rpe'])))
            self.log_table.setItem(i, 5, QTableWidgetItem(log.get('notes', '')))

            if log.get('is_warmup'):
                for col in range(6):
                    item = self.log_table.item(i, col)
                    item.setForeground(QColor("#888888"))
                    item.setBackground(QColor("#222222"))

    def _add_manual_workout(self):
        dialog = ManualWorkoutEntryDialog(self.current_user_id, self)
        if dialog.exec():
            self.refresh_data()

    def _delete_selected_workout(self):
        row = self.workout_table.currentRow()
        if row < 0: return

        workout_id = self.workout_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        confirm = QMessageBox.question(self, "Confirm Delete", "Are you sure you want to permanently delete this workout and all its sets?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if confirm == QMessageBox.StandardButton.Yes:
            WorkoutDatabaseManager.delete_workout(workout_id)
            self.refresh_data()