from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit, 
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, 
    QComboBox, QSpinBox, QSplitter, QListWidget, QAbstractItemView,
    QListWidgetItem
)
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt

from core.db_operations import WorkoutDatabaseManager
from ui.components.body_heatmap import AnatomicalHeatmap, MuscleMapper
from ui.views.base_view import BaseView

class ProgramSandboxView(BaseView):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)

        self.neglected_muscles = []
        
        # QSplitter allows dynamic resizing of the 3 columns
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        
        self._setup_left_panel()
        self._setup_middle_panel()
        self._setup_right_panel()
        
        layout.addWidget(self.splitter)
        
        # Default widths (Heatmap : Bank : Schedule)
        self.splitter.setSizes([350, 250, 500])
        
        self._load_exercise_bank()

    def _setup_left_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        title = QLabel("<b>Live Muscular Feedback</b>")
        title.setStyleSheet("font-size: 16px;")
        layout.addWidget(title)
        
        self.heatmap = AnatomicalHeatmap()
        layout.addWidget(self.heatmap, stretch=1)
        
        # The Smart Assistant (Replaces clicking the SVG)
        self.lbl_assistant = QLabel("<b>Assistant:</b> Add exercises to see feedback.")
        self.lbl_assistant.setWordWrap(True)
        self.lbl_assistant.setStyleSheet("color: #2196F3; padding: 10px; background: #1E1E1E; border-radius: 5px;")
        layout.addWidget(self.lbl_assistant)
        
        self.btn_auto_balance = QPushButton("✨ Auto-Suggest Missing")
        self.btn_auto_balance.setEnabled(False) # Enable once we build the suggestion engine
        layout.addWidget(self.btn_auto_balance)
        
        self.splitter.addWidget(panel)

    def _setup_middle_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.addWidget(QLabel("<b>Exercise Bank</b>"))
        
        # 1. Bodypart Filter
        self.combo_bodypart = QComboBox()
        self.combo_bodypart.addItems(["All Muscles"] + list(MuscleMapper.REGION_MAP.keys()))
        self.combo_bodypart.currentTextChanged.connect(self._refresh_bank_display)
        layout.addWidget(self.combo_bodypart)
        
        # 2. Text Search
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search exercises...")
        self.search_bar.textChanged.connect(self._refresh_bank_display)
        layout.addWidget(self.search_bar)
        
        # 3. Exercise List
        self.exercise_list = QListWidget()
        self.exercise_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.exercise_list.itemDoubleClicked.connect(self._add_to_pool)
        layout.addWidget(self.exercise_list)
        
        self.btn_add = QPushButton("Add to Program ->")
        self.btn_add.clicked.connect(self._add_to_pool)
        layout.addWidget(self.btn_add)
        
        self.splitter.addWidget(panel)

    def _setup_right_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("<b>Program Schedule</b>"))
        
        self.combo_template = QComboBox()
        self.combo_template.addItems(["Custom", "Push/Pull/Legs", "Upper/Lower"])
        header_layout.addWidget(self.combo_template)
        layout.addLayout(header_layout)
        
        # The interactive pool table
        self.pool_table = QTableWidget(0, 4)
        self.pool_table.setHorizontalHeaderLabels(["Exercise", "Sets", "Day", "Action"])
        header = self.pool_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, 4):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.pool_table)
        
        # Fatigue Warning System
        self.lbl_fatigue = QLabel("Daily Volume: Safe")
        self.lbl_fatigue.setStyleSheet("color: #4CAF50; font-weight: bold;")
        layout.addWidget(self.lbl_fatigue)
        
        self.btn_save = QPushButton("Save Program")
        self.btn_save.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 8px;")
        layout.addWidget(self.btn_save)
        
        self.splitter.addWidget(panel)

    # --- LOGIC & CONNECTIONS ---

    def _load_exercise_bank(self):
        self.all_exercises = WorkoutDatabaseManager.get_all_exercises()
        self.exercise_list.clear()
        for ex in self.all_exercises:
            self.exercise_list.addItem(ex['name'])

    def _filter_bank(self, text):
        for i in range(self.exercise_list.count()):
            item = self.exercise_list.item(i)
            item.setHidden(text.lower() not in item.text().lower())

    def _add_to_pool(self):
        selected = self.exercise_list.selectedItems()
        for item in selected:
            if item.flags() == Qt.ItemFlag.NoItemFlags:
                continue # Skip headers
                
            raw_name = item.data(Qt.ItemDataRole.UserRole)
            if not raw_name: 
                raw_name = item.text()
                
            row = self.pool_table.rowCount()
            self.pool_table.insertRow(row)
            
            self.pool_table.setItem(row, 0, QTableWidgetItem(raw_name))
            
            spin_sets = QSpinBox()
            spin_sets.setRange(1, 10)
            spin_sets.setValue(3)
            spin_sets.valueChanged.connect(self._trigger_live_feedback)
            self.pool_table.setCellWidget(row, 1, spin_sets)
            
            combo_day = QComboBox()
            combo_day.addItems(["Unassigned", "Day 1", "Day 2", "Day 3", "Day 4", "Day 5", "Day 6", "Day 7"])
            combo_day.currentTextChanged.connect(self._trigger_live_feedback)
            self.pool_table.setCellWidget(row, 2, combo_day)
            
            btn_remove = QPushButton("X")
            btn_remove.setStyleSheet("color: #F44336;")
            btn_remove.clicked.connect(lambda _, r=row: self._remove_from_pool(r))
            self.pool_table.setCellWidget(row, 3, btn_remove)
            
        # Calling feedback will automatically hide the newly added item from the bank
        self._trigger_live_feedback()

    def _remove_from_pool(self, row):
        self.pool_table.removeRow(row)
        self._trigger_live_feedback() # This will put the item back into the bank

    def _trigger_live_feedback(self):
        exercises_data = []
        day_volumes = {}
        
        for row in range(self.pool_table.rowCount()):
            if not self.pool_table.item(row, 0): continue
            
            name = self.pool_table.item(row, 0).text()
            sets = self.pool_table.cellWidget(row, 1).value()
            day = self.pool_table.cellWidget(row, 2).currentText()
            
            exercises_data.append({'name': name, 'sets': sets})
            if day != "Unassigned":
                day_volumes[day] = day_volumes.get(day, 0) + sets

        # 1. Update Heatmap
        volume_map = WorkoutDatabaseManager.calculate_muscle_volume(exercises_data)
        self.heatmap.update_heatmap(volume_map)
        
        # 2. Check Daily Fatigue
        overloaded_days = [d for d, s in day_volumes.items() if s > 20]
        if overloaded_days:
            self.lbl_fatigue.setText(f"⚠️ High Fatigue: {', '.join(overloaded_days)} exceed 20 sets.")
            self.lbl_fatigue.setStyleSheet("color: #F44336; font-weight: bold;")
        else:
            self.lbl_fatigue.setText("Daily Volume: Optimal")
            self.lbl_fatigue.setStyleSheet("color: #4CAF50; font-weight: bold;")
            
        # 3. Update the Smart Assistant
        core_muscles = ["chest", "latissimus", "shoulders", "quadriceps", "hamstrings", "core"]
        
        if not exercises_data:
            self.lbl_assistant.setText("<b>Assistant:</b> Add exercises to the pool to see feedback.")
            self.lbl_assistant.setStyleSheet("color: #2196F3; padding: 10px; background: #1E1E1E; border-radius: 5px;")
            self.neglected_muscles = []
        else:
            self.neglected_muscles = [m for m in core_muscles if volume_map.get(m, 0) < 3]
            if self.neglected_muscles:
                formatted = [m.title() for m in self.neglected_muscles]
                self.lbl_assistant.setText(f"<b>Assistant:</b> You are neglecting: {', '.join(formatted)}. See suggestions at the top of the bank!")
                self.lbl_assistant.setStyleSheet("color: #FF9800; padding: 10px; background: #2A1F11; border-radius: 5px; border: 1px solid #FF9800;")
            else:
                self.lbl_assistant.setText("<b>Assistant:</b> Your program looks well-balanced! Excellent coverage.")
                self.lbl_assistant.setStyleSheet("color: #4CAF50; padding: 10px; background: #112A18; border-radius: 5px; border: 1px solid #4CAF50;")
                
        # 4. Trigger bank refresh to apply the new neglect filters and sort to top
        self._refresh_bank_display()

    def _refresh_bank_display(self, *args):
        search_text = self.search_bar.text().lower()
        selected_bodypart = self.combo_bodypart.currentText().lower()
        
        # 1. Get exercises currently in the pool (so we can hide them)
        pool_exercises = set()
        for row in range(self.pool_table.rowCount()):
            if self.pool_table.item(row, 0):
                pool_exercises.add(self.pool_table.item(row, 0).text())
                
        self.exercise_list.clear()
        regular_items = []
        suggested_items = []
        
        # 2. Filter exercises
        for ex in self.all_exercises:
            name = ex['name']
            primary = ex['primary_muscle'].lower() if ex['primary_muscle'] else ''
            secondary = ex['secondary_muscles'].lower() if ex['secondary_muscles'] else ''
            
            # Hide if already in pool
            if name in pool_exercises: continue
            # Hide if it fails text search    
            if search_text and search_text not in name.lower(): continue
                
            # Hide if it fails bodypart combobox
            if selected_bodypart != "all muscles":
                targets = MuscleMapper.REGION_MAP.get(selected_bodypart.capitalize(), [selected_bodypart])
                if not any(t in primary or t in secondary for t in targets):
                    continue
                    
            # Sort into 'Suggested' vs 'Regular' based on heatmap analysis
            if hasattr(self, 'neglected_muscles') and primary in self.neglected_muscles:
                suggested_items.append(name)
            else:
                regular_items.append(name)
                
        # 3. Populate QListWidget with formatting
        if suggested_items:
            # Create a non-selectable divider
            header = QListWidgetItem("✨ RECOMMENDED TO BALANCE ✨")
            header.setFlags(Qt.ItemFlag.NoItemFlags)
            header.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            header.setBackground(QColor("#2A1F11"))
            header.setForeground(QColor("#FF9800"))
            self.exercise_list.addItem(header)
            
            for name in sorted(suggested_items):
                item = QListWidgetItem(f"⭐ {name}")
                item.setForeground(QColor("#FF9800"))
                # Save the real name in UserRole data so the program reads "Pull-ups" not "⭐ Pull-ups"
                item.setData(Qt.ItemDataRole.UserRole, name) 
                self.exercise_list.addItem(item)
                
            sep = QListWidgetItem("-" * 30)
            sep.setFlags(Qt.ItemFlag.NoItemFlags)
            sep.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.exercise_list.addItem(sep)
            
        for name in sorted(regular_items):
            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, name)
            self.exercise_list.addItem(item)

    def refresh_data(self):
        """
        Triggered by MainWindow._switch_view().
        Ensures the exercise bank is completely up to date with the database.
        """
        # Save the current search text so we don't clear their search when navigating away and back
        current_search = self.search_bar.text()
        
        # Reload the raw data
        self._load_exercise_bank()
        
        # Re-apply the search filter
        if current_search:
            self._filter_bank(current_search)
        self._trigger_live_feedback()