# ui/views/routine_builder.py
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QListWidget, 
    QTableWidget, QTableWidgetItem, QPushButton, QLabel, 
    QHeaderView, QInputDialog, QMessageBox, QComboBox,
    QCheckBox, QLineEdit, QDialog, QSpinBox, QDoubleSpinBox
)
from PyQt6.QtCore import Qt, QRegularExpression
from PyQt6.QtGui import QRegularExpressionValidator
from core.database import get_connection

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
        self.btn_delete_workout.setStyleSheet("background-color: #f44336; color: white;")
        
        left_btn_layout.addWidget(self.btn_add_workout)
        left_btn_layout.addWidget(self.btn_rename_workout)
        left_btn_layout.addWidget(self.btn_delete_workout)
        left_panel.addLayout(left_btn_layout, stretch=1)
        layout.addLayout(left_panel, stretch=1)

        # --- RIGHT SIDE ---
        right_panel = QVBoxLayout()
        
        header_layout = QHBoxLayout()
        self.lbl_current_template = QLabel("Select a template...")
        self.lbl_current_template.setStyleSheet("font-weight: bold; font-size: 16px;")
        
        self.chk_active = QCheckBox("Include in Current Program")
        self.chk_active.setEnabled(False)
        
        self.btn_analyze = QPushButton("Analyze Split")
        self.btn_analyze.setStyleSheet("background-color: #9C27B0; color: white;")
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
        self.btn_add_ex = QPushButton("+ Add Row")
        self.btn_remove_ex = QPushButton("- Remove Selected Row")
        self.btn_save = QPushButton("Save Template Changes")
        self.btn_save.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        
        btn_layout.addWidget(self.btn_add_ex)
        btn_layout.addWidget(self.btn_remove_ex)
        btn_layout.addWidget(self.btn_save)
        right_panel.addLayout(btn_layout)

        layout.addLayout(right_panel, stretch=3)

        # --- SIGNALS ---
        self.workout_list.currentRowChanged.connect(self._on_template_selected)
        self.chk_active.toggled.connect(self._on_active_toggled)
        self.btn_add_workout.clicked.connect(self._on_add_workout_clicked)
        self.btn_rename_workout.clicked.connect(self._on_rename_workout)
        self.btn_delete_workout.clicked.connect(self._on_delete_workout)
        self.btn_add_ex.clicked.connect(self._on_add_exercise_clicked)
        self.btn_remove_ex.clicked.connect(self._on_remove_row)
        self.btn_save.clicked.connect(self._on_save_clicked)
        self.btn_analyze.clicked.connect(self._on_analyze_clicked)

        self.refresh_data()

    def refresh_data(self):
        self.workout_list.blockSignals(True)
        self.workout_list.clear()
        
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, is_active FROM routine_templates")
        self.all_templates = cursor.fetchall()
        
        cursor.execute("SELECT name FROM exercises ORDER BY name ASC")
        self.exercise_bank = [row['name'] for row in cursor.fetchall()]
        conn.close()

        self._filter_splits(self.search_splits.text())
        self.workout_list.blockSignals(False)

    def _filter_splits(self, text):
        self.workout_list.clear()
        # Sort active splits to the top, then alphabetically
        sorted_templates = sorted(self.all_templates, key=lambda t: (-t['is_active'], t['name'].lower()))
        
        for t in sorted_templates:
            if text.lower() in t['name'].lower():
                prefix = "★ " if t['is_active'] else "   " 
                self.workout_list.addItem(prefix + t['name'])
                item = self.workout_list.item(self.workout_list.count() - 1)
                item.setData(100, t['id'])
                item.setData(101, t['is_active'])

    def _on_template_selected(self, index: int):
        if index < 0: return
        
        item = self.workout_list.item(index)
        template_id = item.data(100)
        self.lbl_current_template.setText(f"Editing: {item.text().replace('★ ', '').strip()}")
        
        self.chk_active.setEnabled(True)
        self.btn_analyze.setEnabled(True)
        self.chk_active.blockSignals(True)
        self.chk_active.setChecked(bool(item.data(101)))
        self.chk_active.blockSignals(False)
        
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
            self._add_validated_row(row, ex['exercise_name'], ex['target_sets'], ex['target_reps'], ex['target_weight'])

    def _add_validated_row(self, row, ex_name, sets=3, reps="8-10", weight=0.0):
        from PyQt6.QtWidgets import QCompleter
        from PyQt6.QtCore import Qt
        
        # 1. Searchable Exercise Dropdown (RESTORED)
        combo = QComboBox()
        combo.setEditable(True) # Required for QCompleter to allow typing
        combo.addItems(self.exercise_bank)
        
        completer = QCompleter(self.exercise_bank)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        combo.setCompleter(completer)
        
        combo.setCurrentText(ex_name)
        self.exercise_table.setCellWidget(row, 0, combo)
        
        # 2. Strict SpinBox for Sets
        spin_sets = QSpinBox()
        spin_sets.setRange(1, 20)
        spin_sets.setValue(int(sets))
        self.exercise_table.setCellWidget(row, 1, spin_sets)
        
        # 3. Regex Validated LineEdit for Reps (e.g., "8" or "8-10")
        line_reps = QLineEdit(str(reps))
        regex = QRegularExpression(r"^\d+(-\d+)?$")
        line_reps.setValidator(QRegularExpressionValidator(regex))
        self.exercise_table.setCellWidget(row, 2, line_reps)
        
        # 4. Strict SpinBox for Weight
        spin_weight = QDoubleSpinBox()
        spin_weight.setRange(0, 1500)
        spin_weight.setSingleStep(2.5)
        spin_weight.setSuffix(" lbs")
        spin_weight.setValue(float(weight))
        self.exercise_table.setCellWidget(row, 3, spin_weight)

    # --- Button Logic ---
    def _on_active_toggled(self, checked):
        item = self.workout_list.currentItem()
        if not item: return
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE routine_templates SET is_active=? WHERE id=?", (1 if checked else 0, item.data(100)))
        conn.commit()
        conn.close()
        item.setData(101, 1 if checked else 0)
        self.refresh_data()

    def _on_add_workout_clicked(self):
        text, ok = QInputDialog.getText(self, "New Split", "Enter name for new workout split:")
        if ok and text:
            conn = get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO routine_templates (name) VALUES (?)", (text,))
                conn.commit()
                self.refresh_data()
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not create template.\n{e}")
            finally:
                conn.close()

    def _on_rename_workout(self):
        item = self.workout_list.currentItem()
        if not item: return
        clean_name = item.text().replace("★ ", "").strip()
        new_name, ok = QInputDialog.getText(self, "Rename", "New Template Name:", text=clean_name)
        if ok and new_name:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE routine_templates SET name=? WHERE id=?", (new_name, item.data(100)))
            conn.commit()
            conn.close()
            self.refresh_data()

    def _on_delete_workout(self):
        item = self.workout_list.currentItem()
        if not item: return
        reply = QMessageBox.question(self, 'Confirm', f"Delete permanently?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM routine_exercises WHERE template_id=?", (item.data(100),))
            cursor.execute("DELETE FROM routine_templates WHERE id=?", (item.data(100),))
            conn.commit()
            conn.close()
            self.refresh_data()

    def _on_add_exercise_clicked(self):
        if not self.workout_list.currentItem(): return
        row = self.exercise_table.rowCount()
        self.exercise_table.insertRow(row)
        self._add_validated_row(row, "New Exercise")

    def _on_remove_row(self):
        current_row = self.exercise_table.currentRow()
        if current_row >= 0:
            self.exercise_table.removeRow(current_row)

    def _on_save_clicked(self):
        current_item = self.workout_list.currentItem()
        if not current_item: return
        template_id = current_item.data(100)
        
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM routine_exercises WHERE template_id = ?", (template_id,))
            for row in range(self.exercise_table.rowCount()):
                # Extract data from validated widgets
                ex_name = self.exercise_table.cellWidget(row, 0).currentText()
                sets = self.exercise_table.cellWidget(row, 1).value()
                reps = self.exercise_table.cellWidget(row, 2).text()
                weight = self.exercise_table.cellWidget(row, 3).value()
                
                cursor.execute('''
                    INSERT INTO routine_exercises 
                    (template_id, exercise_name, target_sets, target_reps, target_weight, is_bodyweight)
                    VALUES (?, ?, ?, ?, ?, 0)
                ''', (template_id, ex_name, sets, reps, weight))
                
            conn.commit()
            QMessageBox.information(self, "Success", "Template saved successfully!")
        except Exception as e:
            conn.rollback()
            QMessageBox.critical(self, "Error", f"Failed to save:\n\n{e}")
        finally:
            conn.close()

    def _on_analyze_clicked(self):
        item = self.workout_list.currentItem()
        if not item: return
        from ui.components.muscle_analyzer import MuscleCoverageDialog
        dialog = MuscleCoverageDialog(item.data(100), item.text().replace("★ ", "").strip(), self)
        dialog.exec()