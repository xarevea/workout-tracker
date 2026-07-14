import csv
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QSpinBox, QSplitter, QListWidget, QAbstractItemView,
    QListWidgetItem, QMessageBox, QDialog, QDoubleSpinBox, QFileDialog,
)
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt, pyqtSignal

from core.db_operations import WorkoutDatabaseManager
from core.models import ExerciseMode
from modules.equipment.plate_calculator import PlateCalculator
from ui.components.body_heatmap import AnatomicalHeatmap, MuscleMapper
from ui.views.base_view import BaseView

class ProgramScheduleList(QListWidget):
    """Custom List to handle Drag and Drop from the Exercise Bank."""
    scheduleChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setDropIndicatorShown(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat('application/x-qabstractitemmodeldatalist'):
            event.accept()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat('application/x-qabstractitemmodeldatalist'):
            event.accept()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.source() == self:
            # Reordering internally
            super().dropEvent(event)
            self.scheduleChanged.emit() # Safely alerts the parent view without referencing MainWindow

        elif event.source() is not None:
            # Dropped from Exercise Bank QListWidget
            drop_row = self.indexAt(event.position().toPoint()).row()
            if drop_row == -1: drop_row = self.count()

            for item in event.source().selectedItems():
                ex_name = item.data(Qt.ItemDataRole.UserRole)
                if not ex_name: ex_name = item.text()

                new_item = QListWidgetItem(ex_name)
                new_item.setData(Qt.ItemDataRole.UserRole, ex_name)
                self.insertItem(drop_row, new_item)
                drop_row += 1

            event.acceptProposedAction()
            self.scheduleChanged.emit()

class FinalizeProgramDialog(QDialog):
    def __init__(self, exercises_data, user_id, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.setWindowTitle("Finalize Program Details")
        self.resize(950, 500)
        self.layout = QVBoxLayout(self)

        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("Global Default Rest (s):"))

        self.spin_default_rest = QSpinBox()
        self.spin_default_rest.setRange(0, 600)
        self.spin_default_rest.setValue(90)
        self.spin_default_rest.valueChanged.connect(self._apply_default_rest)
        header_layout.addWidget(self.spin_default_rest)

        header_layout.addStretch()

        btn_snap = QPushButton("🧲 Auto-Snap Weights to My Equipment")
        btn_snap.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
        btn_snap.setToolTip("Adjusts all target weights to the closest valid combination using your Garage inventory.")
        btn_snap.clicked.connect(self._snap_to_equipment)
        header_layout.addStretch()
        header_layout.addWidget(btn_snap)

        self.layout.addLayout(header_layout)

        self.table = QTableWidget(len(exercises_data), 9)
        self.table.setHorizontalHeaderLabels(["Day", "Exercise", "Mode", "Group", "Sets", "Min Target", "Max Target", "Weight", "Rest (s)"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.layout.addWidget(self.table)

        for row, ex in enumerate(exercises_data):
            is_timed = ex.get('tracks_time', False)
            day_item = QTableWidgetItem(ex['day'])
            day_item.setFlags(Qt.ItemFlag.ItemIsEnabled)

            display_name = f"{ex['name']} ⏱️" if is_timed else ex['name']
            ex_item = QTableWidgetItem(ex['name'])
            ex_item.setFlags(Qt.ItemFlag.ItemIsEnabled)

            combo_mode = QComboBox()
            for mode_enum in ExerciseMode:
                combo_mode.addItem(mode_enum.value, userData=mode_enum)

            current_mode = ex.get('mode', ExerciseMode.STANDARD)
            idx = combo_mode.findData(current_mode)
            if idx >= 0:
                combo_mode.setCurrentIndex(idx)

            spin_group = QSpinBox()
            spin_group.setToolTip("Exercises with the same Group # run together in a circuit.")

            spin_sets = QSpinBox()
            spin_sets.setValue(ex.get('sets', 3))

            spin_min = QSpinBox()
            spin_min.setMaximum(9999)
            spin_min.setSuffix(" sec" if is_timed else " rep")
            spin_min.setValue(ex.get('min_reps', 30 if is_timed else 8))

            spin_max = QSpinBox()
            spin_max.setMaximum(9999)
            spin_max.setSuffix(" sec" if is_timed else " rep")
            spin_max.setValue(ex.get('max_reps', 60 if is_timed else 12))

            spin_wt = QDoubleSpinBox()
            spin_wt.setRange(0, 1000)
            spin_wt.setValue(ex.get('weight', 0.0))

            spin_rest = QSpinBox()
            spin_rest.setRange(0, 600)
            spin_rest.setValue(ex.get('rest', 90))
            spin_rest.setSingleStep(15)

            self.table.setItem(row, 0, day_item)
            self.table.setItem(row, 1, ex_item)
            self.table.setCellWidget(row, 2, combo_mode)
            self.table.setCellWidget(row, 3, spin_group)
            self.table.setCellWidget(row, 4, spin_sets)
            self.table.setCellWidget(row, 5, spin_min)
            self.table.setCellWidget(row, 6, spin_max)
            self.table.setCellWidget(row, 7, spin_wt)
            self.table.setCellWidget(row, 8, spin_rest)

        btn_save = QPushButton("Confirm & Save Program")
        btn_save.setStyleSheet("background-color: #4CAF50; color: white; padding: 10px; font-weight: bold;")
        btn_save.clicked.connect(self.accept)
        self.layout.addWidget(btn_save)

    def _apply_default_rest(self, value):
        for row in range(self.table.rowCount()):
            self.table.cellWidget(row, 8).setValue(value)

    def _snap_to_equipment(self):
        for row in range(self.table.rowCount()):
            spin_wt = self.table.cellWidget(row, 7)
            target = spin_wt.value()
            if target > 0:
                valid_weight = PlateCalculator.get_closest_valid_weight(target, self.user_id)
                spin_wt.setValue(valid_weight)

    def get_final_data(self):
        final_data = []
        for row in range(self.table.rowCount()):
            raw_ex_name = self.table.item(row, 1).text().replace(" ⏱️", "")
            final_data.append({
                'day': self.table.item(row, 0).text(),
                'exercise': raw_ex_name,
                'mode': self.table.cellWidget(row, 2).currentData(),
                'circuit_group': self.table.cellWidget(row, 3).value(),
                'sets': self.table.cellWidget(row, 4).value(),
                'min_reps': self.table.cellWidget(row, 5).value(),
                'max_reps': self.table.cellWidget(row, 6).value(),
                'weight': self.table.cellWidget(row, 7).value(),
                'rest': self.table.cellWidget(row, 8).value(),
            })
        return final_data

class ProgramSandboxView(BaseView):
    # __init__ and left panel setup remain identical
    def __init__(self, parent=None):
        super().__init__(parent)
        self.all_exercises = []
        self.neglected_muscles = []
        self.show_balance_suggestions = False

        layout = QHBoxLayout(self)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        self._setup_left_panel()
        self._setup_middle_panel()
        self._setup_right_panel()

        layout.addWidget(self.splitter)
        self.splitter.setSizes([350, 250, 500])
        self._load_exercise_bank()

    def _setup_left_panel(self):
        # Unchanged from your original code
        panel = QWidget()
        layout = QVBoxLayout(panel)

        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("<b>Analysis View:</b>"))
        self.combo_analysis_view = QComboBox()
        self.combo_analysis_view.addItems(["Overall Program"])
        self.combo_analysis_view.currentTextChanged.connect(self._trigger_live_feedback)
        header_layout.addWidget(self.combo_analysis_view)
        layout.addLayout(header_layout)

        self.heatmap = AnatomicalHeatmap()
        self.heatmap.regionClicked.connect(self._on_heatmap_clicked)
        layout.addWidget(self.heatmap, stretch=1)

        self.lbl_assistant = QLabel("<b>Assistant:</b> Add exercises to see feedback.")
        self.lbl_assistant.setWordWrap(True)
        self.lbl_assistant.setStyleSheet("color: #2196F3; padding: 10px; background: #1E1E1E; border-radius: 5px;")
        layout.addWidget(self.lbl_assistant)

        self.splitter.addWidget(panel)

    def refresh_data(self):
        current_search = self.search_bar.text()
        self._load_exercise_bank()

        self.combo_load_program.blockSignals(True)
        self.combo_load_program.clear()
        self.combo_load_program.addItem("-- Create New Program --", userData=None)
        programs = WorkoutDatabaseManager.get_programs_for_user(self.current_user_id)
        for p in programs:
            self.combo_load_program.addItem(p['name'], userData=p['id'])
        self.combo_load_program.blockSignals(False)

        self.combo_load_program.setCurrentIndex(0)
        self._load_existing_program()

        if current_search: self._filter_bank(current_search)
        self._trigger_live_feedback()

    def _setup_middle_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.addWidget(QLabel("<b>Exercise Bank</b>"))

        self.combo_bodypart = QComboBox()
        self.combo_bodypart.addItems(["All Muscles"] + list(MuscleMapper.REGION_MAP.keys()))
        self.combo_bodypart.currentTextChanged.connect(self._refresh_bank_display)
        layout.addWidget(self.combo_bodypart)

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search exercises...")
        self.search_bar.textChanged.connect(self._refresh_bank_display)
        layout.addWidget(self.search_bar)

        self.btn_toggle_balance = QPushButton("🧠 Show Balancing Suggestions")
        self.btn_toggle_balance.setCheckable(True)
        self.btn_toggle_balance.toggled.connect(self._toggle_balance_suggestions)
        layout.addWidget(self.btn_toggle_balance)

        # Configure drag from Bank
        self.exercise_list = QListWidget()
        self.exercise_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.exercise_list.setDragEnabled(True)
        self.exercise_list.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)
        layout.addWidget(self.exercise_list)

        self.splitter.addWidget(panel)

    def _setup_right_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)

        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("<b>Program Schedule</b>"))

        self.combo_load_program = QComboBox()
        self.combo_load_program.addItem("-- Create New Program --", userData=None)
        self.combo_load_program.currentIndexChanged.connect(self._load_existing_program)
        header_layout.addWidget(self.combo_load_program)
        layout.addLayout(header_layout)

        self.txt_program_name = QLineEdit()
        self.txt_program_name.setPlaceholderText("Enter Program Name...")
        layout.addWidget(self.txt_program_name)

        self.schedule_list = ProgramScheduleList()
        self.schedule_list.itemDoubleClicked.connect(self._remove_from_schedule)

        self.schedule_list.scheduleChanged.connect(self._trigger_live_feedback)

        layout.addWidget(self.schedule_list)

        self.lbl_fatigue = QLabel("Daily Volume: Safe")
        self.lbl_fatigue.setStyleSheet("color: #4CAF50; font-weight: bold;")
        layout.addWidget(self.lbl_fatigue)

        self.btn_save = QPushButton("Configure && Save Program")
        self.btn_save.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 8px;")
        self.btn_save.clicked.connect(self._save_program)
        layout.addWidget(self.btn_save)

        self.btn_import_csv = QPushButton("📥 Import Program from CSV")
        self.btn_import_csv.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold; padding: 8px;")
        self.btn_import_csv.clicked.connect(self._import_from_csv)
        layout.addWidget(self.btn_import_csv)

        self.splitter.addWidget(panel)

    def _remove_from_schedule(self, item):
        if not item.data(Qt.ItemDataRole.UserRole + 1):  # Don't delete headers
            self.schedule_list.takeItem(self.schedule_list.row(item))
            self._trigger_live_feedback()

    def _load_exercise_bank(self):
        self.all_exercises = WorkoutDatabaseManager.get_all_exercises()
        self.exercise_list.clear()
        for ex in self.all_exercises:
            self.exercise_list.addItem(ex['name'])

    def _load_existing_program(self):
        program_id = self.combo_load_program.currentData()
        self.schedule_list.clear()

        if not program_id:
            self.txt_program_name.clear()
            self._init_empty_days()
            self._trigger_live_feedback()
            return

        self.txt_program_name.setText(self.combo_load_program.currentText())
        data = WorkoutDatabaseManager.get_sandbox_program_data(program_id)

        day_map = {d: [] for d in ["Unassigned", "Day 1", "Day 2", "Day 3", "Day 4", "Day 5", "Day 6", "Day 7"]}
        # FIX: Append the whole dictionary 'item', not just item['exercise']
        for item in data: day_map[item['day']].append(item)

        for day, ex_list in day_map.items():
            # Add Horizontal Separator Header
            header = QListWidgetItem(f"--- {day} ---")
            header.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            header.setBackground(QColor("#333333"))
            header.setForeground(QColor("#FF9800"))
            header.setFlags(header.flags() & ~Qt.ItemFlag.ItemIsDragEnabled & ~Qt.ItemFlag.ItemIsSelectable)
            header.setData(Qt.ItemDataRole.UserRole + 1, day)
            self.schedule_list.addItem(header)

            for ex in ex_list:
                item = QListWidgetItem(ex['exercise'])       # Display the string
                item.setData(Qt.ItemDataRole.UserRole, ex)   # Store the WHOLE dict in the background!
                self.schedule_list.addItem(item)

        self._trigger_live_feedback()

    def _init_empty_days(self):
        for day in ["Unassigned", "Day 1", "Day 2", "Day 3", "Day 4", "Day 5", "Day 6", "Day 7"]:
            header = QListWidgetItem(f"--- {day} ---")
            header.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            header.setBackground(QColor("#333333"))
            header.setForeground(QColor("#FF9800"))
            header.setFlags(header.flags() & ~Qt.ItemFlag.ItemIsDragEnabled & ~Qt.ItemFlag.ItemIsSelectable)
            header.setData(Qt.ItemDataRole.UserRole + 1, day)
            self.schedule_list.addItem(header)

    def _get_current_schedule_data(self):
        exercises_data = []
        current_day = "Unassigned"

        ex_dict_lookup = {e['name']: e.get('tracks_time', False) for e in self.all_exercises}

        for i in range(self.schedule_list.count()):
            item = self.schedule_list.item(i)
            is_header = item.data(Qt.ItemDataRole.UserRole + 1)

            if is_header:
                current_day = is_header
            else:
                user_data = item.data(Qt.ItemDataRole.UserRole)

                # FIX: If it's loaded from the DB it's a dict, if it's newly dragged from the bank it's a string
                if isinstance(user_data, dict):
                    ex_name = user_data['exercise']
                    base_dict = user_data
                else:
                    ex_name = user_data
                    base_dict = {}

                is_timed = ex_dict_lookup.get(ex_name, False)

                exercises_data.append({
                    'name': ex_name,
                    'day': current_day,
                    'tracks_time': is_timed,

                    # Pre-fill with existing values if they exist, otherwise use logical defaults
                    'sets': base_dict.get('sets', 3),
                    'min_reps': base_dict.get('min_reps', 30 if is_timed else 8),
                    'max_reps': base_dict.get('max_reps', 60 if is_timed else 12),
                    'weight': base_dict.get('weight', 0.0),
                    'rest': base_dict.get('rest', 90),
                    'mode': base_dict.get('mode', ExerciseMode.STANDARD),
                    'circuit_group': base_dict.get('circuit_group', 0)
                })
        return exercises_data

    def _save_program(self):
        name = self.txt_program_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Error", "Please enter a program name.")
            return

        exercises_data = self._get_current_schedule_data()
        if not exercises_data:
            QMessageBox.warning(self, "Error", "Your schedule is empty!")
            return

        dialog = FinalizeProgramDialog(exercises_data, self.current_user_id, self)
        if dialog.exec():
            final_data = dialog.get_final_data()
            WorkoutDatabaseManager.save_sandbox_program(
                user_id=self.current_user_id,
                program_id=self.combo_load_program.currentData(),
                program_name=name,
                pool_data=final_data
            )
            QMessageBox.information(self, "Success", f"Program '{name}' saved successfully!")
            self.refresh_data()

    def _on_heatmap_clicked(self, muscle_name: str, region_name: str):
        if self.combo_bodypart.findText(region_name) != -1:
            self.combo_bodypart.setCurrentText(region_name)

    def _toggle_balance_suggestions(self, checked):
        self.show_balance_suggestions = checked
        if checked:
            self.btn_toggle_balance.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
        else:
            self.btn_toggle_balance.setStyleSheet("")
        self._refresh_bank_display()

    def _filter_bank(self, text):
        for i in range(self.exercise_list.count()):
            item = self.exercise_list.item(i)
            item.setHidden(text.lower() not in item.text().lower())

    def _refresh_bank_display(self, *args):
        search_text = self.search_bar.text().lower()
        selected_bodypart = self.combo_bodypart.currentText().lower()

        pool_exercises = {ex['name'] for ex in self._get_current_schedule_data()}
        self.exercise_list.clear()

        regular_items = []
        suggested_items = []

        for ex in self.all_exercises:
            name = ex['name']
            primary = ex['primary_muscle'].lower() if ex['primary_muscle'] else ''
            secondary = ex['secondary_muscles'].lower() if ex['secondary_muscles'] else ''

            if name in pool_exercises: continue
            if search_text and search_text not in name.lower(): continue

            if selected_bodypart != "all muscles":
                # FIX: Get the targets and ensure everything is space-separated instead of hyphens
                targets = MuscleMapper.REGION_MAP.get(selected_bodypart.title(), [])
                norm_targets = [t.replace('-', ' ').lower() for t in targets] + [selected_bodypart]

                norm_pri = primary.replace('-', ' ')
                norm_sec = secondary.replace('-', ' ')

                # Check if ANY target is inside the primary or secondary strings
                if not any(t in norm_pri or t in norm_sec for t in norm_targets):
                    continue

            if self.show_balance_suggestions and primary in self.neglected_muscles:
                suggested_items.append(name)
            else:
                regular_items.append(name)

        if suggested_items:
            header = QListWidgetItem("✨ RECOMMENDED TO BALANCE ✨")
            header.setFlags(Qt.ItemFlag.NoItemFlags); header.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            header.setBackground(QColor("#2A1F11")); header.setForeground(QColor("#FF9800"))
            self.exercise_list.addItem(header)

            for name in sorted(suggested_items):
                item = QListWidgetItem(f"⭐ {name}")
                item.setForeground(QColor("#FF9800")); item.setData(Qt.ItemDataRole.UserRole, name)
                self.exercise_list.addItem(item)

            sep = QListWidgetItem("-" * 30); sep.setFlags(Qt.ItemFlag.NoItemFlags)
            sep.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.exercise_list.addItem(sep)

        for name in sorted(regular_items):
            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, name)
            self.exercise_list.addItem(item)

    def _trigger_live_feedback(self):
        active_view = self.combo_analysis_view.currentText()
        schedule_data = self._get_current_schedule_data()

        exercises_data = []
        day_volumes = {}
        active_days = set()

        for ex in schedule_data:
            day = ex['day']
            if day != "Unassigned":
                active_days.add(day)
                day_volumes[day] = day_volumes.get(day, 0) + 3 # Assumed 3 sets for live estimate

            if active_view == "Overall Program" or active_view == day:
                exercises_data.append({'name': ex['name'], 'sets': 3})

        current_options = [self.combo_analysis_view.itemText(i) for i in range(self.combo_analysis_view.count())]
        needed_options = ["Overall Program"] + sorted(list(active_days))
        if current_options != needed_options:
            self.combo_analysis_view.blockSignals(True)
            self.combo_analysis_view.clear()
            self.combo_analysis_view.addItems(needed_options)
            if active_view in needed_options:
                self.combo_analysis_view.setCurrentText(active_view)
            self.combo_analysis_view.blockSignals(False)

        volume_map = WorkoutDatabaseManager.calculate_muscle_volume(exercises_data)
        self.heatmap.update_heatmap(volume_map)

        overloaded_days = [d for d, s in day_volumes.items() if s > 20]
        if overloaded_days:
            self.lbl_fatigue.setText(f"⚠️ High Fatigue: {', '.join(overloaded_days)} exceed 20 sets.")
            self.lbl_fatigue.setStyleSheet("color: #F44336; font-weight: bold;")
        else:
            self.lbl_fatigue.setText("Daily Volume: Optimal")
            self.lbl_fatigue.setStyleSheet("color: #4CAF50; font-weight: bold;")

        if active_view == "Overall Program":
            # Map raw volume strings to broad regions
            region_volume = {r.lower(): 0 for r in MuscleMapper.REGION_MAP.keys()}
            for k, v in volume_map.items():
                k_lower = k.lower().replace(' ', '-')
                for region, slugs in MuscleMapper.REGION_MAP.items():
                    if k_lower == region.lower() or k_lower in slugs:
                        region_volume[region.lower()] += v
                        break

            # Find neglected top-level regions
            self.neglected_muscles = [m for m in region_volume.keys() if region_volume.get(m, 0) < 3]

            if not exercises_data:
                self.lbl_assistant.setText("<b>Assistant:</b> Add exercises to the schedule to see feedback.")
                self.lbl_assistant.setStyleSheet("color: #2196F3;")
            elif self.neglected_muscles:
                self.lbl_assistant.setText(f"<b>Assistant:</b> Neglected areas: {', '.join([m.title() for m in self.neglected_muscles])}.")
                self.lbl_assistant.setStyleSheet("color: #FF9800;")
            else:
                self.lbl_assistant.setText("<b>Assistant:</b> Well balanced!")
                self.lbl_assistant.setStyleSheet("color: #4CAF50;")
        else:
            self.lbl_assistant.setText(f"<b>{active_view} Stats:</b> {day_volumes.get(active_view, 0)} Total Sets.")
            self.lbl_assistant.setStyleSheet("color: #2196F3;")

        self._refresh_bank_display()

    def _import_from_csv(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Import Program CSV", "", "CSV Files (*.csv)")
        if not file_path: return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                pool_data = []

                for row in reader:
                    # Clean up the Day format (ensuring it fits "Day 1", "Day 2", etc.)
                    day = row.get('Day', 'Day 1').strip()
                    if not day.startswith('Day'):
                        day = f"Day {day}"

                    ex_name = row.get('Exercise', '').strip()
                    if not ex_name: continue

                    # Auto-add the exercise to the DB if it doesn't exist
                    WorkoutDatabaseManager.add_exercise(
                        name=ex_name, primary="Unknown", secondary="", cues="Imported from CSV"
                    )

                    # Append to pool data matching the format save_sandbox_program expects
                    pool_data.append({
                        'day': day,
                        'exercise': ex_name,
                        'sets': int(row.get('Sets', 3) or 3),
                        'min_reps': int(row.get('Min_Reps', 8) or 8),
                        'max_reps': int(row.get('Max_Reps', 12) or 12),
                        'weight': float(row.get('Weight', 0.0) or 0.0),
                        'rest': int(row.get('Rest_Seconds', 90) or 90)
                    })

            if not pool_data:
                QMessageBox.warning(self, "Error", "No valid exercises found in CSV.")
                return

            prog_name = self.txt_program_name.text().strip() or "Imported Program"

            # Pass to Database Manager to save as a new program
            WorkoutDatabaseManager.save_sandbox_program(
                user_id=self.current_user_id,
                program_id=None,  # 'None' forces the creation of a new program
                program_name=prog_name,
                pool_data=pool_data
            )

            QMessageBox.information(self, "Success", f"'{prog_name}' imported successfully!")
            self.refresh_data()

        except Exception as e:
            QMessageBox.critical(self, "Import Failed", f"Error reading CSV:\n{str(e)}")