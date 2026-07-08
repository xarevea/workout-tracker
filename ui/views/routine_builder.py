# ui/views/routine_builder.py
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QListWidget, 
    QTableWidget, QTableWidgetItem, QPushButton, QLabel, 
    QHeaderView, QInputDialog, QMessageBox, QComboBox,
    QCheckBox, QLineEdit, QSpinBox, QDoubleSpinBox, QCompleter,
    QSizePolicy
)
from PyQt6.QtCore import Qt

from core.db_operations import WorkoutDatabaseManager
from core.events import event_bus
from ui.components.muscle_analyzer import MuscleCoverageDialog

class RoutineBuilderView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)

        # --- LEFT SIDE ---
        left_panel = QVBoxLayout()
        left_panel.addWidget(QLabel("Your Workout Templates"))
        self.search_splits = QLineEdit()
        self.search_splits.setPlaceholderText("Search splits...")
        self.search_splits.textChanged.connect(self._filter_splits)
        left_panel.addWidget(self.search_splits)
        
        self.workout_list = QListWidget()
        left_panel.addWidget(self.workout_list)
        
        left_btn_layout = QHBoxLayout()
        self.btn_add_workout = QPushButton("+ New Split")
        self.btn_rename_workout = QPushButton("Rename")
        self.btn_delete_workout = QPushButton("Delete")
        left_btn_layout.addWidget(self.btn_add_workout)
        left_btn_layout.addWidget(self.btn_rename_workout)
        left_btn_layout.addWidget(self.btn_delete_workout)
        left_panel.addLayout(left_btn_layout, stretch=1)
        layout.addLayout(left_panel, stretch=1)

        # --- RIGHT SIDE ---
        right_panel = QVBoxLayout()
        header_layout = QHBoxLayout()
        self.lbl_current_template = QLabel("Select a template...")
        self.chk_active = QCheckBox("Include in Current Program")
        self.btn_analyze = QPushButton("Analyze Split")
        header_layout.addWidget(self.lbl_current_template)
        header_layout.addStretch()
        header_layout.addWidget(self.chk_active)
        header_layout.addWidget(self.btn_analyze)
        right_panel.addLayout(header_layout)
        
        # 6 Columns now (Added Reorder Controls, Min/Max Reps)
        self.exercise_table = QTableWidget(0, 7) 
        self.exercise_table.setHorizontalHeaderLabels(["Order", "Exercise", "Sets", "Min Reps", "Max Reps", "Weight", "Rest (s)"])
        
        # Ensure Exercise name stretches, others wrap to content
        header = self.exercise_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents) # Up/Down arrows
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)          # Exercise Name gets all extra room
        for i in range(2, 7):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents) # Sets, Reps, Wt, Rest

        right_panel.addWidget(self.exercise_table)

        btn_layout = QHBoxLayout()
        self.btn_add_ex = QPushButton("+ Add Row")
        self.btn_remove_ex = QPushButton("- Remove Selected Row")
        self.btn_save = QPushButton("Save Template Changes")
        btn_layout.addWidget(self.btn_add_ex)
        btn_layout.addWidget(self.btn_remove_ex)
        btn_layout.addWidget(self.btn_save)
        right_panel.addLayout(btn_layout)

        layout.addLayout(right_panel, stretch=3)

        # --- SIGNALS ---
        self.workout_list.currentRowChanged.connect(self._on_template_selected)
        self.chk_active.toggled.connect(self._on_active_toggled)
        self.btn_add_workout.clicked.connect(self._on_add_workout_clicked)
        self.btn_add_ex.clicked.connect(self._on_add_exercise_clicked)
        self.btn_remove_ex.clicked.connect(self._on_remove_row)
        self.btn_save.clicked.connect(self._on_save_clicked)
        
        # Subscribe to Global Event Bus
        event_bus.data_changed.connect(self.refresh_data)
        self.refresh_data()

    def refresh_data(self):
        self.workout_list.blockSignals(True)
        # Use Manager instead of Raw SQL
        self.all_templates = WorkoutDatabaseManager.get_all_templates()
        ex_data = WorkoutDatabaseManager.get_all_exercises()
        self.exercise_bank = [ex['name'] for ex in ex_data]
        self._filter_splits(self.search_splits.text())
        self.workout_list.blockSignals(False)

    def _filter_splits(self, text):
        self.workout_list.clear()
        sorted_templates = sorted(self.all_templates, key=lambda t: (-t['is_active'], t['name'].lower()))
        for t in sorted_templates:
            if text.lower() in t['name'].lower():
                prefix = "★ " if t['is_active'] else "   " 
                self.workout_list.addItem(prefix + t['name'])
                self.workout_list.item(self.workout_list.count() - 1).setData(100, t['id'])

    def _on_template_selected(self, index: int):
        if index < 0: return
        template_id = self.workout_list.item(index).data(100)
        self.exercise_table.setRowCount(0)
        
        # Use Manager instead of Raw SQL
        exercises = WorkoutDatabaseManager.get_routine_exercises(template_id)
        for row, ex in enumerate(exercises):
            self.exercise_table.insertRow(row)
            self._add_validated_row(row, ex['name'], ex['target_sets'], ex['target_reps_min'], ex['target_reps_max'], ex['target_weight'], ex['rest_seconds'])

    def _add_validated_row(self, row, ex_name, sets=3, min_r=8, max_r=10, weight=0.0, rest=90):
        # 0. REORDER CONTROLS
        ctrl_widget = QWidget()
        ctrl_layout = QHBoxLayout(ctrl_widget)
        ctrl_layout.setContentsMargins(0,0,0,0)
        btn_up = QPushButton("↑")
        btn_up.clicked.connect(lambda: self._move_row(ctrl_widget, -1))
        btn_down = QPushButton("↓")
        btn_down.clicked.connect(lambda: self._move_row(ctrl_widget, 1))
        ctrl_layout.addWidget(btn_up); ctrl_layout.addWidget(btn_down)
        self.exercise_table.setCellWidget(row, 0, ctrl_widget)

        # 1. EXERCISE COMBO
        combo = QComboBox()
        combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        combo.setMinimumWidth(150) # Prevent it from collapsing completely
        combo.setEditable(True)
        combo.addItems(self.exercise_bank)
        completer = QCompleter(self.exercise_bank)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        combo.setCompleter(completer)
        combo.setCurrentText(ex_name)
        self.exercise_table.setCellWidget(row, 1, combo)
        
        # 2-6. SPINBOXES
        spin_sets = QSpinBox(); spin_sets.setValue(int(sets))
        # Create the spinboxes
        spin_min = QSpinBox()
        spin_min.setValue(int(min_r))
        spin_max = QSpinBox()
        spin_max.setValue(int(max_r))
        spin_min.valueChanged.connect(lambda val: spin_max.setMinimum(val))
        spin_max.valueChanged.connect(lambda val: spin_min.setMaximum(val))

        spin_wt = QDoubleSpinBox(); spin_wt.setRange(0, 1500); spin_wt.setValue(float(weight))
        spin_rest = QSpinBox(); spin_rest.setRange(0, 600); spin_rest.setSingleStep(15); spin_rest.setValue(int(rest))
        
        self.exercise_table.setCellWidget(row, 2, spin_sets)
        self.exercise_table.setCellWidget(row, 3, spin_min)
        self.exercise_table.setCellWidget(row, 4, spin_max)
        self.exercise_table.setCellWidget(row, 5, spin_wt)
        self.exercise_table.setCellWidget(row, 6, spin_rest)

    def _move_row(self, widget, direction):
        row = self.exercise_table.indexAt(widget.pos()).row()
        target_row = row + direction
        if target_row < 0 or target_row >= self.exercise_table.rowCount(): return
        
        # Extract existing
        ex = self.exercise_table.cellWidget(row, 1).currentText()
        s = self.exercise_table.cellWidget(row, 2).value()
        m1 = self.exercise_table.cellWidget(row, 3).value()
        m2 = self.exercise_table.cellWidget(row, 4).value()
        w = self.exercise_table.cellWidget(row, 5).value()
        r = self.exercise_table.cellWidget(row, 6).value()
        
        self.exercise_table.removeRow(row)
        self.exercise_table.insertRow(target_row)
        self._add_validated_row(target_row, ex, s, m1, m2, w, r)

    def _on_add_exercise_clicked(self):
        row = self.exercise_table.rowCount()
        self.exercise_table.insertRow(row)
        self._add_validated_row(row, "New Exercise")

    def _on_remove_row(self):
        r = self.exercise_table.currentRow()
        if r >= 0: self.exercise_table.removeRow(r)

    def _on_save_clicked(self):
        item = self.workout_list.currentItem()
        if not item: return
        template_id = item.data(100)
        
        ex_data = []
        for r in range(self.exercise_table.rowCount()):
            ex_data.append({
                'name': self.exercise_table.cellWidget(r, 1).currentText(),
                'sets': self.exercise_table.cellWidget(r, 2).value(),
                'min_reps': self.exercise_table.cellWidget(r, 3).value(),
                'max_reps': self.exercise_table.cellWidget(r, 4).value(),
                'weight': self.exercise_table.cellWidget(r, 5).value(),
                'rest': self.exercise_table.cellWidget(r, 6).value()
            })
            
        WorkoutDatabaseManager.save_routine_exercises(template_id, ex_data)
        event_bus.data_changed.emit() # Inform other tabs
        QMessageBox.information(self, "Saved", "Template updated successfully.")

    def _on_active_toggled(self, checked):
        pass # Handle DB update 
    def _on_add_workout_clicked(self):
        pass