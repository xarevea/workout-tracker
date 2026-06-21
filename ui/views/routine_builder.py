from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QListWidget, 
    QTableWidget, QTableWidgetItem, QPushButton, QLabel, 
    QHeaderView, QInputDialog, QMessageBox, QComboBox, 
    QCheckBox, QLineEdit, QCompleter, QDialog,
    QSpinBox, QDoubleSpinBox
)
from PyQt6.QtGui import QRegularExpressionValidator
from PyQt6.QtCore import QRegularExpression

from core.database import get_connection

class RoutineBuilderView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)

        # --- LEFT SIDE: Workout Days ---
        left_panel = QVBoxLayout()
        left_panel.addWidget(QLabel("Your Workout Templates"))

        # New Search Bar
        self.search_splits = QLineEdit()
        self.search_splits.setPlaceholderText("Search splits...")
        self.search_splits.textChanged.connect(self._filter_splits)
        left_panel.addWidget(self.search_splits)

        self.workout_list = QListWidget()
        left_panel.addWidget(self.workout_list)
        
        self.btn_add_workout = QPushButton("+ Create New Split")
        left_panel.addWidget(self.btn_add_workout)
        layout.addLayout(left_panel, stretch=1)

        # --- RIGHT SIDE: Exercise Editor ---
        right_panel = QVBoxLayout()
        header_layout = QHBoxLayout()
        self.lbl_current_template = QLabel("Select a template...")
        self.lbl_current_template.setStyleSheet("font-weight: bold; font-size: 16px;")
        
        self.chk_active = QCheckBox("Include in Current Program")
        self.chk_active.toggled.connect(self._on_active_toggled)
        self.chk_active.setEnabled(False)
        
        self.btn_analyze = QPushButton("Analyze Split")
        self.btn_analyze.setStyleSheet("background-color: #9C27B0; color: white;")
        self.btn_analyze.clicked.connect(self._on_analyze_clicked)
        self.btn_analyze.setEnabled(False)

        header_layout.addWidget(self.lbl_current_template)
        header_layout.addStretch()
        header_layout.addWidget(self.chk_active)
        header_layout.addWidget(self.btn_analyze)
        right_panel.addLayout(header_layout)
        
        self.exercise_table = QTableWidget(0, 4)
        self.exercise_table.setHorizontalHeaderLabels(["Exercise", "Sets", "Reps", "Target Weight"])
        self.exercise_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        right_panel.addWidget(self.exercise_table)

        btn_layout = QHBoxLayout()
        self.btn_add_ex = QPushButton("+ Add Exercise")
        self.btn_save = QPushButton("Save Template Changes")
        self.btn_save.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        
        btn_layout.addWidget(self.btn_add_ex)
        btn_layout.addWidget(self.btn_save)
        right_panel.addLayout(btn_layout)

        layout.addLayout(right_panel, stretch=3)

        # Update LEFT panel buttons
        left_btn_layout = QHBoxLayout()
        self.btn_add_workout = QPushButton("+ New Split")
        self.btn_rename_workout = QPushButton("Rename")
        self.btn_delete_workout = QPushButton("Delete")
        self.btn_delete_workout.setStyleSheet("background-color: #f44336; color: white;")
        
        left_btn_layout.addWidget(self.btn_add_workout)
        left_btn_layout.addWidget(self.btn_rename_workout)
        left_btn_layout.addWidget(self.btn_delete_workout)
        left_panel.addLayout(left_btn_layout)

        # Update RIGHT panel buttons
        btn_layout = QHBoxLayout()
        self.btn_add_ex = QPushButton("+ Add Row")
        self.btn_remove_ex = QPushButton("- Remove Selected Row")
        self.btn_save = QPushButton("Save Template Changes")
        self.btn_save.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        
        btn_layout.addWidget(self.btn_add_ex)
        btn_layout.addWidget(self.btn_remove_ex)
        btn_layout.addWidget(self.btn_save)
        right_panel.addLayout(btn_layout)

        # Pre-fetch the Exercise Bank
        self.exercise_bank = self._fetch_exercise_bank()

        # --- SIGNAL CONNECTIONS ---
        self.btn_rename_workout.clicked.connect(self._on_rename_workout)
        self.btn_delete_workout.clicked.connect(self._on_delete_workout)
        self.btn_remove_ex.clicked.connect(self._on_remove_row)
        self.workout_list.currentRowChanged.connect(self._on_template_selected)
        self.btn_add_workout.clicked.connect(self._on_add_workout_clicked)
        self.btn_add_ex.clicked.connect(self._on_add_exercise_clicked)
        self.btn_save.clicked.connect(self._on_save_clicked)

        # Load initial data
        self.refresh_data()

    def _fetch_exercise_bank(self):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM exercises ORDER BY name ASC")
        results = [row['name'] for row in cursor.fetchall()]
        conn.close()
        # Fallback if DB is empty
        return results if results else ["Bench Press", "Squat", "Deadlift"]

    def _on_add_exercise_clicked(self):
        if not self.workout_list.currentItem(): return
        row = self.exercise_table.rowCount()
        self.exercise_table.insertRow(row)
        
        # Searchable Combo Box!
        combo = QComboBox()
        combo.setEditable(True)
        combo.addItems(self.exercise_bank)
        
        completer = QCompleter(self.exercise_bank)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        combo.setCompleter(completer)
        
        self.exercise_table.setCellWidget(row, 0, combo)
        
        # 2. Strict defaults
        self.exercise_table.setItem(row, 1, QTableWidgetItem("3"))
        self.exercise_table.setItem(row, 2, QTableWidgetItem("8-10"))
        self.exercise_table.setItem(row, 3, QTableWidgetItem("BW"))

    def _on_analyze_clicked(self):
        item = self.workout_list.currentItem()
        if not item: return
        
        # Pops up the heatmap just for this specific workout
        from ui.components.body_heatmap import AnatomicalHeatmap
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Analysis: {item.text()}")
        dialog.resize(600, 400)
        
        layout = QVBoxLayout(dialog)
        heatmap = AnatomicalHeatmap()
        layout.addWidget(heatmap)
        
        # Reuse our dashboard logic but filter by template_id
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT e.primary_muscle, e.secondary_muscles, r.target_sets
            FROM routine_exercises r
            JOIN exercises e ON r.exercise_name = e.name
            WHERE r.template_id = ?
        ''', (item.data(100),))
        
        volume_map = {}
        for ex in cursor.fetchall():
            sets = ex['target_sets']
            if ex['primary_muscle']: volume_map[ex['primary_muscle']] = volume_map.get(ex['primary_muscle'], 0) + sets
            if ex['secondary_muscles']:
                for sec in [s.strip() for s in ex['secondary_muscles'].split(',')]:
                    volume_map[sec] = volume_map.get(sec, 0) + (sets * 0.5)
        conn.close()
        
        heatmap.update_heatmap(volume_map)
        dialog.exec()

    def _on_remove_row(self):
        current_row = self.exercise_table.currentRow()
        if current_row >= 0:
            self.exercise_table.removeRow(current_row)

    def _on_rename_workout(self):
        item = self.workout_list.currentItem()
        if not item: return
        
        new_name, ok = QInputDialog.getText(self, "Rename", "New Template Name:", text=item.text())
        if ok and new_name:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE routine_templates SET name=? WHERE id=?", (new_name, item.data(100)))
            conn.commit()
            conn.close()
            item.setText(new_name)

    def _on_delete_workout(self):
        item = self.workout_list.currentItem()
        if not item: return
        
        reply = QMessageBox.question(self, 'Confirm', f"Delete '{item.text()}' permanently?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM routine_exercises WHERE template_id=?", (item.data(100),))
            cursor.execute("DELETE FROM routine_templates WHERE id=?", (item.data(100),))
            conn.commit()
            conn.close()
            self.refresh_data()

    def _on_active_toggled(self, checked):
        item = self.workout_list.currentItem()
        if not item: return
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE routine_templates SET is_active=? WHERE id=?", (1 if checked else 0, item.data(100)))
        conn.commit()
        conn.close()
        item.setData(101, 1 if checked else 0)

    def refresh_data(self):
        """Fetches all templates from the SQLite database."""
        self.workout_list.blockSignals(True)
        self.workout_list.clear()
        
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, is_active FROM routine_templates")
        self.all_templates = cursor.fetchall()
        conn.close()
        
        self._filter_splits(self.search_splits.text())
            
        self.workout_list.blockSignals(False)

    def _filter_splits(self, text):
        self.workout_list.clear()
        # SORTING LOGIC: Active splits (1) float to the top, then sort alphabetically
        sorted_templates = sorted(self.all_templates, key=lambda t: (-t['is_active'], t['name'].lower()))
        
        for t in sorted_templates:
            if text.lower() in t['name'].lower():
                # Add a visual indicator for Active programs
                prefix = "★ " if t['is_active'] else "   " 
                self.workout_list.addItem(prefix + t['name'])
                item = self.workout_list.item(self.workout_list.count() - 1)
                item.setData(100, t['id'])
                item.setData(101, t['is_active'])

    def _on_template_selected(self, index: int):
        if index < 0: return
        item = self.workout_list.item(index)
        
        # Update UI Controls
        self.lbl_current_template.setText(f"Editing: {item.text()}")
        self.chk_active.setEnabled(True)
        self.btn_analyze.setEnabled(True)
        
        self.chk_active.blockSignals(True)
        self.chk_active.setChecked(bool(item.data(101)))
        self.chk_active.blockSignals(False)
        
        template_id = item.data(100)
        
        self.exercise_table.setRowCount(0)
        
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT exercise_name, target_sets, target_reps, target_weight, is_bodyweight 
            FROM routine_exercises WHERE template_id = ?
        ''', (template_id,))
        exercises = cursor.fetchall()
        conn.close()

        for row, ex in enumerate(exercises):
            self.exercise_table.insertRow(row)
            self.exercise_table.setItem(row, 0, QTableWidgetItem(ex['exercise_name']))
            self.exercise_table.setItem(row, 1, QTableWidgetItem(str(ex['target_sets'])))
            self.exercise_table.setItem(row, 2, QTableWidgetItem(ex['target_reps']))
            
            weight_display = "BW" if ex['is_bodyweight'] else f"{ex['target_weight']} lbs"
            self.exercise_table.setItem(row, 3, QTableWidgetItem(weight_display))

    # --- NEW BUTTON LOGIC ---

    def _on_add_workout_clicked(self):
        """Prompts the user for a new routine name and adds it to the database."""
        text, ok = QInputDialog.getText(self, "New Split", "Enter name for new workout split (e.g., 'Day 1 - Upper'):")
        if ok and text:
            conn = get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO routine_templates (name) VALUES (?)", (text,))
                conn.commit()
                self.refresh_data()
                # Select the newly created item
                self.workout_list.setCurrentRow(self.workout_list.count() - 1)
            except Exception as e:
                QMessageBox.warning(self, "Database Error", f"Could not create template. It might already exist.\n\n{e}")
            finally:
                conn.close()

    def _on_add_exercise_clicked(self):
        """Appends a new, blank row to the table."""
        # Ensure a template is actually selected first
        if not self.workout_list.currentItem():
            QMessageBox.warning(self, "Warning", "Please select or create a Workout Template first.")
            return
            
        current_row_count = self.exercise_table.rowCount()
        self.exercise_table.insertRow(current_row_count)
        
        # Populate with default dummy data so it isn't empty
        self.exercise_table.setItem(current_row_count, 0, QTableWidgetItem("New Exercise"))
        self.exercise_table.setItem(current_row_count, 1, QTableWidgetItem("3"))
        self.exercise_table.setItem(current_row_count, 2, QTableWidgetItem("8-10"))
        self.exercise_table.setItem(current_row_count, 3, QTableWidgetItem("BW"))

    def _on_save_clicked(self):
        """Scrapes the table and saves the exercises to the database."""
        current_item = self.workout_list.currentItem()
        if not current_item:
            return
            
        template_id = current_item.data(100)
        
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # 1. Delete the old routine exercises for this template to avoid duplicates
            cursor.execute("DELETE FROM routine_exercises WHERE template_id = ?", (template_id,))
            
            # 2. Iterate through the table and insert the new layout
            for row in range(self.exercise_table.rowCount()):
                widget = self.exercise_table.cellWidget(row, 0)
                ex_name = widget.currentText() if widget else self.exercise_table.item(row, 0).text()
                
                # Failsafe parsing for sets and weights
                try:
                    sets = int(self.exercise_table.item(row, 1).text())
                except ValueError:
                    sets = 1 
                    
                reps = self.exercise_table.item(row, 2).text()
                weight_str = self.exercise_table.item(row, 3).text()
                
                is_bw = 1 if "BW" in weight_str.upper() else 0
                weight = 0.0
                
                if not is_bw:
                    try:
                        # Extract just the number (e.g., turns "225 lbs" into 225.0)
                        weight = float(weight_str.lower().replace('lbs', '').strip())
                    except ValueError:
                        weight = 0.0
                        
                cursor.execute('''
                    INSERT INTO routine_exercises 
                    (template_id, exercise_name, target_sets, target_reps, target_weight, is_bodyweight)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (template_id, ex_name, sets, reps, weight, is_bw))
                
            conn.commit()
            QMessageBox.information(self, "Success", f"'{current_item.text()}' saved successfully!")
            
        except Exception as e:
            conn.rollback()
            QMessageBox.critical(self, "Error", f"Failed to save template:\n\n{e}")
        finally:
            conn.close()