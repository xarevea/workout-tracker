# ========================================
# FILE PATH: ui/views/exercise_dictionary.py
# ========================================
import qtawesome as qta
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, 
    QListWidget, QComboBox, QPlainTextEdit, QSplitter, QMessageBox,
    QFileDialog,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QMovie

from core.db_operations import WorkoutDatabaseManager
from core.events import event_bus
from ui.components.body_heatmap import MuscleMapper
from ui.views.base_view import BaseView

class ExerciseDictionaryView(BaseView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.all_exercises = []
        self.current_ex_id = None
        
        layout = QVBoxLayout(self)
        title = QLabel("Exercise Dictionary")
        title.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # --- LEFT PANEL: Searchable List ---
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search exercises...")
        self.search_bar.textChanged.connect(self._filter_list)
        left_layout.addWidget(self.search_bar)
        
        self.ex_list = QListWidget()
        self.ex_list.itemSelectionChanged.connect(self._on_exercise_selected)
        left_layout.addWidget(self.ex_list)
        
        btn_new = QPushButton("+ Create New Exercise")
        btn_new.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
        btn_new.clicked.connect(self._prepare_new_exercise)
        left_layout.addWidget(btn_new)
        
        splitter.addWidget(left_panel)

        # --- RIGHT PANEL: Details & Editing ---
        right_panel = QWidget()
        self.right_layout = QVBoxLayout(right_panel)
        self.right_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.txt_name = QLineEdit()
        self.right_layout.addWidget(QLabel("Exercise Name:"))
        self.right_layout.addWidget(self.txt_name)
        
        muscle_groups = MuscleMapper.get_ui_muscle_list(include_empty=True)
        
        self.combo_primary = QComboBox()
        self.combo_primary.addItems(muscle_groups)
        self.right_layout.addWidget(QLabel("Primary Muscle Target:"))
        self.right_layout.addWidget(self.combo_primary)
        
        self.txt_secondary = QLineEdit()
        self.txt_secondary.setPlaceholderText("e.g. triceps, core, lower-back")
        self.right_layout.addWidget(QLabel("Secondary Muscles (Comma Separated):"))
        self.right_layout.addWidget(self.txt_secondary)
        
        self.txt_cues = QPlainTextEdit()
        self.txt_cues.setPlaceholderText("1. Cue one\n2. Cue two")
        self.right_layout.addWidget(QLabel("Form Cues (Shown during workout):"))
        self.right_layout.addWidget(self.txt_cues)
        
        action_layout = QHBoxLayout()
        self.btn_save = QPushButton("Save Changes")
        self.btn_save.setStyleSheet("background-color: #4CAF50; color: white;")
        self.btn_save.clicked.connect(self._save_exercise)
        
        self.btn_delete = QPushButton("Delete")
        self.btn_delete.setStyleSheet("background-color: #F44336; color: white;")
        self.btn_delete.clicked.connect(self._delete_exercise)
        
        action_layout.addWidget(self.btn_delete)
        action_layout.addStretch()
        action_layout.addWidget(self.btn_save)
        
        self.right_layout.addLayout(action_layout)

        # --- MEDIA PLAYER ---
        self.lbl_media = QLabel("No Media Selected")
        self.lbl_media.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_media.setFixedSize(250, 250)
        self.lbl_media.setStyleSheet("background-color: #111111; border: 1px solid #333; border-radius: 8px;")
        
        self.txt_media_path = QLineEdit()
        self.txt_media_path.setPlaceholderText("Path to GIF/Image...")
        
        btn_browse = QPushButton(qta.icon('fa5s.folder-open', color='white'), "")
        btn_browse.clicked.connect(self._browse_media)
        
        media_input_layout = QHBoxLayout()
        media_input_layout.addWidget(self.txt_media_path)
        media_input_layout.addWidget(btn_browse)

        self.right_layout.addWidget(self.lbl_media)
        self.right_layout.addLayout(media_input_layout)

        splitter.addWidget(right_panel)
        
        splitter.setSizes([300, 500])
        layout.addWidget(splitter)
        
        self._set_editor_enabled(False)

    def _browse_media(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Exercise Media", "", "Images/GIFs (*.png *.jpg *.jpeg *.gif)")
        if file_path:
            self.txt_media_path.setText(file_path)
            self._load_media(file_path)

    def _load_media(self, path):
        if not path:
            self.lbl_media.setText("No Media Selected")
            return
            
        if path.lower().endswith('.gif'):
            self.movie = QMovie(path)
            self.lbl_media.setMovie(self.movie)
            self.movie.start()
        else:
            from PyQt6.QtGui import QPixmap
            pix = QPixmap(path).scaled(self.lbl_media.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.lbl_media.setPixmap(pix)

    def refresh_data(self):
        self.all_exercises = WorkoutDatabaseManager.get_all_exercises()
        self._filter_list()
        
    def _filter_list(self):
        search_txt = self.search_bar.text().lower()
        self.ex_list.blockSignals(True)
        self.ex_list.clear()
        
        for ex in self.all_exercises:
            if search_txt in ex['name'].lower():
                self.ex_list.addItem(ex['name'])
                self.ex_list.item(self.ex_list.count() - 1).setData(Qt.ItemDataRole.UserRole, ex['id'])
                
        self.ex_list.blockSignals(False)

    def _set_editor_enabled(self, enabled: bool):
        self.txt_name.setEnabled(enabled)
        self.combo_primary.setEnabled(enabled)
        self.txt_secondary.setEnabled(enabled)
        self.txt_cues.setEnabled(enabled)
        self.btn_save.setEnabled(enabled)
        self.btn_delete.setEnabled(enabled and self.current_ex_id is not None)

    def _prepare_new_exercise(self):
        self.ex_list.clearSelection()
        self.current_ex_id = None
        self.txt_name.clear()
        self.combo_primary.setCurrentIndex(0)
        self.txt_secondary.clear()
        self.txt_cues.clear()
        self._set_editor_enabled(True)
        self.txt_name.setFocus()

    def _on_exercise_selected(self):
        items = self.ex_list.selectedItems()
        if not items:
            self._set_editor_enabled(False)
            return
            
        ex_id = items[0].data(Qt.ItemDataRole.UserRole)
        ex = next((e for e in self.all_exercises if e['id'] == ex_id), None)
        if not ex: return
        
        self.current_ex_id = ex_id
        self.txt_name.setText(ex['name'])
        
        # Safely Title-Case the DB slug to match the UI Dropdown (e.g., "upper-back" -> "Upper-Back")
        primary_str = ex['primary_muscle'].title() if ex['primary_muscle'] else ""
        primary_idx = self.combo_primary.findText(primary_str)
        self.combo_primary.setCurrentIndex(max(0, primary_idx))
        
        self.txt_secondary.setText(ex['secondary_muscles'] or "")
        self.txt_cues.setPlainText(ex['cues'] or "")
        self._set_editor_enabled(True)

    def _save_exercise(self):
        name = self.txt_name.text().strip()
        if not name: return QMessageBox.warning(self, "Error", "Exercise name required.")
        
        if self.current_ex_id:
            WorkoutDatabaseManager.update_exercise(
                self.current_ex_id, name, "Hybrid", 
                self.combo_primary.currentText(), self.txt_secondary.text(), self.txt_cues.toPlainText()
            )
        else:
            WorkoutDatabaseManager.add_exercise(
                name=name, 
                primary=self.combo_primary.currentText(), 
                secondary=self.txt_secondary.text(),
                cues=self.txt_cues.toPlainText(),
            ) 
            
        self.refresh_data()
        event_bus.data_changed.emit()
        QMessageBox.information(self, "Saved", f"'{name}' saved successfully.")

    def _delete_exercise(self):
        if not self.current_ex_id: return
        confirm = QMessageBox.question(self, "Confirm Delete", "Are you sure? This cannot be undone.", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm == QMessageBox.StandardButton.Yes:
            WorkoutDatabaseManager.delete_exercise(self.current_ex_id)
            self.current_ex_id = None
            self._set_editor_enabled(False)
            self.refresh_data()
            event_bus.data_changed.emit()