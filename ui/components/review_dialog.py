from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QDoubleSpinBox, QSpinBox, QWidget, QListWidget, QSplitter
)
from PyQt6.QtCore import Qt

from core.db_operations import WorkoutDatabaseManager
from ui.components.body_heatmap import AnatomicalHeatmap, MuscleMapper

class ExerciseSwapDialog(QDialog):
    def __init__(self, current_exercise_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Swap Exercise: {current_exercise_name}")
        self.resize(800, 500)
        self.selected_new_exercise = current_exercise_name

        self.all_ex = WorkoutDatabaseManager.get_all_exercises()
        current_ex = next((e for e in self.all_ex if e['name'] == current_exercise_name), None)
        primary = current_ex['primary_muscle'] if current_ex else ""

        layout = QHBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Heatmap Left
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.addWidget(QLabel("Filter by Muscle:"))

        self.heatmap = AnatomicalHeatmap()
        self.heatmap.regionClicked.connect(self._on_heatmap_clicked)
        left_layout.addWidget(self.heatmap)
        splitter.addWidget(left_widget)

        # List Right
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        self.lbl_filter = QLabel(f"Showing matches for: {primary.title() if primary else 'All'}")
        right_layout.addWidget(self.lbl_filter)

        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        right_layout.addWidget(self.list_widget)

        btn_confirm = QPushButton("Confirm Swap")
        btn_confirm.setStyleSheet("background-color: #4CAF50; color: white;")
        btn_confirm.clicked.connect(self._confirm)
        right_layout.addWidget(btn_confirm)
        splitter.addWidget(right_widget)

        layout.addWidget(splitter)

        # Init map
        vol_map = {primary: 15} if primary else {}
        self.heatmap.update_heatmap(vol_map)
        self._filter_list(primary)

    def _on_heatmap_clicked(self, slug, region):
        vol_map = {region: 15}
        self.heatmap.update_heatmap(vol_map)
        self.lbl_filter.setText(f"Showing matches for: {region}")
        self._filter_list(region)

    def _filter_list(self, target_muscle):
        self.list_widget.clear()
        target = target_muscle.lower()

        for ex in self.all_ex:
            pri = ex['primary_muscle'].lower() if ex['primary_muscle'] else ""
            sec = ex['secondary_muscles'].lower() if ex['secondary_muscles'] else ""

            # Show if target matches primary, secondary, or if no target is selected
            if not target or target in pri or target in sec:
                self.list_widget.addItem(ex['name'])

    def _on_item_double_clicked(self, item):
        self.selected_new_exercise = item.text()
        self.accept()

    def _confirm(self):
        item = self.list_widget.currentItem()
        if item:
            self.selected_new_exercise = item.text()
        self.accept()


class WorkoutReviewDialog(QDialog):
    def __init__(self, session_logs, progression_suggestions, current_settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Workout Review & Progression")
        self.resize(1100, 400)
        self.suggestions = progression_suggestions
        self.current_settings = current_settings
        self.final_adjustments = {}
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        self.table = QTableWidget(len(self.suggestions), 5)
        self.table.setHorizontalHeaderLabels(["Exercise", "Current Target", "Engine Suggestion", "Final Decision", "Swap"])
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

            btn_swap = QPushButton("🔄 Change Exercise")
            btn_swap.clicked.connect(lambda checked, r=row, ex=exercise_name: self._swap_exercise(r, ex))
            self.table.setCellWidget(row, 4, btn_swap)

            self.final_adjustments[exercise_name] = {
                'weight': spin_wt, 'min_reps': spin_min, 'max_reps': spin_max, 'new_name': exercise_name
            }

        layout.addWidget(self.table)
        btn_approve = QPushButton("Approve & Update Routine")
        btn_approve.setStyleSheet("background-color: #4CAF50; color: white; height: 30px;")
        btn_approve.clicked.connect(self.accept)
        layout.addWidget(btn_approve)

    def _swap_exercise(self, row, old_name):
        dialog = ExerciseSwapDialog(old_name, self)
        if dialog.exec():
            new_name = dialog.selected_new_exercise
            self.final_adjustments[old_name]['new_name'] = new_name
            self.table.item(row, 0).setText(f"{old_name} ➔ {new_name}")
            self.table.item(row, 0).setForeground(QColor("#FF9800"))

    def get_final_targets(self):
        results = {}
        for exercise, widgets in self.final_adjustments.items():
            results[exercise] = {
                'weight': widgets['weight'].value(),
                'min_reps': widgets['min_reps'].value(),
                'max_reps': widgets['max_reps'].value(),
                'new_name': widgets['new_name']
            }
        return results