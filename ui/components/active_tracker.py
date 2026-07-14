# ui/components/active_tracker.py
import os
import time
from collections import defaultdict, Counter
from enum import Enum, auto
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSpinBox, QDoubleSpinBox, QSlider,
    QGroupBox, QScrollArea, QComboBox, QCheckBox,
    QDialog, QTableWidget, QTableWidgetItem, QLineEdit, QHeaderView
)
from PyQt6.QtCore import Qt, QTimer, QUrl, QThreadPool, QRectF
from PyQt6.QtGui import QPainter, QPen, QColor, QFont
from PyQt6.QtMultimedia import QSoundEffect
from PyQt6.QtWidgets import QSystemTrayIcon, QStyle
from PyQt6.QtTextToSpeech import QTextToSpeech

from core.db_operations import WorkoutDatabaseManager
from core.events import event_bus
from modules.equipment.plate_calculator import PlateCalculator
from modules.progression.engine import ProgressionEngine
from modules.workout.session import FitbitSyncWorker
from ui.components.barbell_view import BarbellVisualizer
from ui.components.body_heatmap import AnatomicalHeatmap
from ui.components.review_dialog import WorkoutReviewDialog

class SetState(Enum):
    IDLE = auto()
    BUFFER = auto()
    ACTIVE = auto()
    OVERTIME = auto()

class WarmupPreviewDialog(QDialog):
    def __init__(self, warmups, is_timed, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Review Warm-Up Sets")
        self.resize(400, 300)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Edit, add, or remove generated warm-ups:"))

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Reps/Secs", "Weight (lbs)", ""])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.table)

        for w in warmups:
            self._add_row_ui(w['reps'], w['weight'])

        btn_layout = QHBoxLayout()
        btn_add = QPushButton("+ Add Set")
        btn_add.clicked.connect(lambda: self._add_row_ui(10, 0))

        btn_confirm = QPushButton("Accept Warm-ups")
        btn_confirm.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        btn_confirm.clicked.connect(self.accept)

        btn_layout.addWidget(btn_add)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_confirm)
        layout.addLayout(btn_layout)

    def _add_row_ui(self, reps, weight):
        row = self.table.rowCount()
        self.table.insertRow(row)

        spin_reps = QSpinBox(); spin_reps.setRange(0, 1000); spin_reps.setValue(reps)
        spin_wt = QDoubleSpinBox(); spin_wt.setRange(0, 1500); spin_wt.setValue(weight)

        btn_del = QPushButton("X"); btn_del.setStyleSheet("color: red;")
        btn_del.clicked.connect(lambda checked, b=btn_del: self.table.removeRow(
            next((i for i in range(self.table.rowCount()) if self.table.cellWidget(i, 2) == b), -1)
        ))

        self.table.setCellWidget(row, 0, spin_reps)
        self.table.setCellWidget(row, 1, spin_wt)
        self.table.setCellWidget(row, 2, btn_del)

    def get_warmups(self):
        res = []
        for r in range(self.table.rowCount()):
            res.append({
                "reps": self.table.cellWidget(r, 0).value(),
                "weight": self.table.cellWidget(r, 1).value()
            })
        return res

class WorkoutFinalizationDialog(QDialog):
    def __init__(self, logs, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit & Finalize Sets Before Save")
        self.resize(850, 450)
        self.logs = logs

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Review your logged sets. Any sets you skipped are not shown here."))

        self.table = QTableWidget(len(logs), 7)
        self.table.setHorizontalHeaderLabels(["Exercise", "Set", "Reps/Secs", "Weight (lbs)", "RPE", "Warmup", "Notes"])

        for row, log in enumerate(logs):
            self.table.setItem(row, 0, QTableWidgetItem(log['exercise']))
            self.table.item(row, 0).setFlags(Qt.ItemFlag.ItemIsEnabled)

            self.table.setItem(row, 1, QTableWidgetItem(str(log['set'])))
            self.table.item(row, 1).setFlags(Qt.ItemFlag.ItemIsEnabled)

            spin_reps = QSpinBox(); spin_reps.setRange(0, 1000); spin_reps.setValue(log['reps'])
            self.table.setCellWidget(row, 2, spin_reps)

            spin_wt = QDoubleSpinBox(); spin_wt.setRange(0, 1500); spin_wt.setValue(log['weight'])
            self.table.setCellWidget(row, 3, spin_wt)

            spin_rpe = QDoubleSpinBox(); spin_rpe.setRange(1, 10); spin_rpe.setValue(log['rpe'])
            self.table.setCellWidget(row, 4, spin_rpe)

            chk_warmup = QCheckBox(); chk_warmup.setChecked(log.get('is_warmup', False))
            self.table.setCellWidget(row, 5, chk_warmup)

            txt_notes = QLineEdit(); txt_notes.setText(log.get('notes', ''))
            self.table.setCellWidget(row, 6, txt_notes)

        btn_save = QPushButton("Save & Continue to Progression Suggestions")
        btn_save.setStyleSheet("background-color: #4CAF50; color: white; padding: 10px; font-weight: bold;")
        btn_save.clicked.connect(self.accept)
        layout.addWidget(self.table)
        layout.addWidget(btn_save)

    def get_final_logs(self):
        final = []
        for r, log in enumerate(self.logs):
            log['reps'] = self.table.cellWidget(r, 2).value()
            log['weight'] = self.table.cellWidget(r, 3).value()
            log['rpe'] = self.table.cellWidget(r, 4).value()
            log['is_warmup'] = self.table.cellWidget(r, 5).isChecked()
            log['notes'] = self.table.cellWidget(r, 6).text()
            final.append(log)
        return final

class MiniWorkoutWidget(QWidget):
    def __init__(self, main_tracker, parent=None):
        super().__init__(parent, Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.main_tracker = main_tracker
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.setFixedSize(240, 135)

        self.frame = QWidget(self)
        self.frame.setGeometry(0, 0, 240, 135)
        self.frame.setStyleSheet("background-color: rgba(30, 30, 30, 230); border-radius: 10px; border: 1px solid #555; color: white;")

        layout = QVBoxLayout(self.frame)
        layout.setContentsMargins(10, 5, 10, 10)

        top_row = QHBoxLayout()
        top_row.addStretch()
        self.btn_close = QPushButton("×")
        self.btn_close.setFixedSize(20, 20)
        self.btn_close.setStyleSheet("background: transparent; color: #888; border: none; font-weight: bold; font-size: 16px;")
        self.btn_close.clicked.connect(self._close_overlay)
        top_row.addWidget(self.btn_close)
        layout.addLayout(top_row)

        self.lbl_status = QLabel("Idle")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setStyleSheet("font-weight: bold; font-size: 14px; background: transparent; border: none;")

        self.lbl_target = QLabel("")
        self.lbl_target.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_target.setStyleSheet("color: #b0b0b0; font-size: 12px; background: transparent; border: none;")

        self.lbl_timer = QLabel("00:00")
        self.lbl_timer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_timer.setStyleSheet("color: #4CAF50; font-size: 20px; font-weight: bold; background: transparent; border: none;")

        self.btn_action = QPushButton("Action")
        self.btn_action.setMinimumHeight(35)
        self.btn_action.setStyleSheet("background-color: #2196F3; font-weight: bold; border-radius: 5px; padding: 5px;")
        self.btn_action.clicked.connect(self._on_action)

        layout.addWidget(self.lbl_status)
        layout.addWidget(self.lbl_target)
        layout.addWidget(self.lbl_timer)
        layout.addWidget(self.btn_action)

        self.oldPos = self.pos()
        self.is_resting = False

    def _close_overlay(self):
        self.main_tracker.chk_mini_timer.setChecked(False)
        self.hide()

    def set_display(self, status, time_str, is_resting, target_info=""):
        self.lbl_status.setText(status)
        self.lbl_timer.setText(time_str)
        self.lbl_target.setText(target_info)
        self.is_resting = is_resting

        if is_resting:
            self.lbl_timer.setStyleSheet("color: #FF9800; font-size: 20px; font-weight: bold; background: transparent; border: none;")
            self.btn_action.setText("Skip Rest")
            self.btn_action.setStyleSheet("background-color: #FF9800; font-weight: bold; border-radius: 5px; padding: 5px;")
        else:
            self.lbl_timer.setStyleSheet("color: #4CAF50; font-size: 20px; font-weight: bold; background: transparent; border: none;")
            self.btn_action.setText("Log Set")
            self.btn_action.setStyleSheet("background-color: #2196F3; font-weight: bold; border-radius: 5px; padding: 5px;")

    def _on_action(self):
        if self.is_resting:
            self.main_tracker._skip_rest()
        else:
            task = self.main_tracker.controller.get_current_task()
            if not task: return

            dialog = QDialog(self, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
            dialog.setStyleSheet("background-color: #2d2d2d; border: 1px solid #777; border-radius: 8px; color: white; padding: 10px;")
            d_layout = QVBoxLayout(dialog)

            d_layout.addWidget(QLabel(f"Log: {task['exercise']['name']}"))

            row1 = QHBoxLayout()
            spin_reps = QSpinBox(); spin_reps.setRange(0, 1000)
            spin_reps.setValue(self.main_tracker.spin_reps.value())
            row1.addWidget(QLabel("Reps/Secs:")); row1.addWidget(spin_reps)

            row2 = QHBoxLayout()
            spin_wt = QDoubleSpinBox(); spin_wt.setRange(0, 1500)
            spin_wt.setValue(self.main_tracker.spin_weight.value())
            row2.addWidget(QLabel("Weight:")); row2.addWidget(spin_wt)

            row3 = QHBoxLayout()
            spin_rpe = QDoubleSpinBox(); spin_rpe.setRange(1, 10); spin_rpe.setValue(self.main_tracker.slider_rpe.value())
            chk_warmup = QCheckBox("Warm-up Set")
            chk_warmup.setChecked(self.main_tracker.chk_warmup.isChecked())
            row3.addWidget(QLabel("RPE:")); row3.addWidget(spin_rpe)
            row3.addWidget(chk_warmup)

            txt_notes = QLineEdit()
            txt_notes.setPlaceholderText("Notes...")

            btn_submit = QPushButton("Submit")
            btn_submit.setStyleSheet("background-color: #4CAF50; padding: 5px; font-weight: bold;")
            btn_submit.clicked.connect(dialog.accept)

            d_layout.addLayout(row1)
            d_layout.addLayout(row2)
            d_layout.addLayout(row3)
            d_layout.addWidget(txt_notes)
            d_layout.addWidget(btn_submit)

            if dialog.exec():
                self.main_tracker.spin_reps.setValue(spin_reps.value())
                self.main_tracker.spin_weight.setValue(spin_wt.value())
                self.main_tracker.slider_rpe.setValue(int(spin_rpe.value()))
                self.main_tracker.chk_warmup.setChecked(chk_warmup.isChecked())
                self.main_tracker.txt_notes.setText(txt_notes.text())
                self.main_tracker._on_log_set_clicked()

    def mousePressEvent(self, event):
        self.oldPos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        delta = event.globalPosition().toPoint() - self.oldPos
        self.move(self.x() + delta.x(), self.y() + delta.y())
        self.oldPos = event.globalPosition().toPoint()


class ActiveTrackerWidget(QWidget):
    def __init__(self, controller, minimap, global_timer_lbl=None, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.minimap = minimap
        self.global_timer_lbl = global_timer_lbl

        self.workout_seconds = 0
        self.rest_seconds = 0
        self.audio_enabled = True
        self.warning_threshold_sec = 5

        self.active_set_state = SetState.IDLE
        self.buffer_remaining = 0
        self.set_time_remaining = 0
        self.current_left_loadout = []
        self._last_exercise_name = None

        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
        self.tray.show()

        self.mini_timer = MiniWorkoutWidget(self)
        self.tts = QTextToSpeech()

        self._setup_audio()
        self._setup_ui()
        self._setup_timers()

        self.minimap.nodeClicked.connect(self._preview_exercise)

    def announce(self, text: str):
        if self.audio_enabled and self.chk_voice.isChecked() and self.tts:
            self.tts.say(text)

    def refresh_data(self):
        if self.controller.is_active: return

        self.combo_workout_selector.blockSignals(True)
        self.combo_workout_selector.clear()

        templates = WorkoutDatabaseManager.get_program_templates(self.controller.current_program_id)
        if not templates:
            self.combo_workout_selector.addItem("-- No Program / Rest Day --")
        else:
            for t in templates:
                if f"Day {t['day_number']}" in t['name']:
                    self.combo_workout_selector.addItem(t['name'], userData=t['id'])
                else:
                    self.combo_workout_selector.addItem(f"{t['name']} (Day {t['day_number']})", userData=t['id'])

        self.combo_workout_selector.blockSignals(False)

        if self.combo_workout_selector.count() > 0 and self.combo_workout_selector.currentData():
            self._load_selected_workout()
        else:
            self.lbl_exercise_name.setText("Select a Program")

    def _load_selected_workout(self):
        template_id = self.combo_workout_selector.currentData()
        if template_id:
            if self.controller.is_active:
                self._toggle_timer()

            self.workout_seconds = 0
            self.rest_seconds = 0
            self._reset_timed_set()
            self.lbl_timer.setText("00:00")
            self.lbl_timer.setStyleSheet("color: white;")
            self.controller.start_time = 0
            self._last_exercise_name = None

            self.rest_container.hide()
            self.log_group.setEnabled(True)
            self.btn_log.setEnabled(False)

            self.controller.template_name = self.combo_workout_selector.currentText()
            self.controller.load_template(template_id)
            self._update_display()

    def _setup_audio(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        tick_path = os.path.join(base_dir, '..', '..', 'assets', 'tick.wav')
        bell_path = os.path.join(base_dir, '..', '..', 'assets', 'bell.wav')

        self.snd_tick = QSoundEffect()
        if os.path.exists(tick_path):
            self.snd_tick.setSource(QUrl.fromLocalFile(tick_path))

        self.snd_bell = QSoundEffect()
        if os.path.exists(bell_path):
            self.snd_bell.setSource(QUrl.fromLocalFile(bell_path))

    def _play_sound(self, sound_type: str):
        if not self.audio_enabled: return
        if sound_type == "tick" and self.snd_tick.source().isValid(): self.snd_tick.play()
        elif sound_type == "bell" and self.snd_bell.source().isValid(): self.snd_bell.play()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        workout_select_layout = QHBoxLayout()
        self.combo_workout_selector = QComboBox()
        self.combo_workout_selector.currentIndexChanged.connect(self._load_selected_workout)
        workout_select_layout.addWidget(QLabel("Today's Workout:"))
        workout_select_layout.addWidget(self.combo_workout_selector, stretch=1)
        layout.addLayout(workout_select_layout)

        timer_layout = QHBoxLayout()
        self.lbl_timer = QLabel("00:00")
        self.lbl_timer.setFont(QFont("Arial", 36, QFont.Weight.Bold))
        self.btn_play_pause = QPushButton("Start Workout")
        self.btn_play_pause.setFixedSize(120, 40)
        self.btn_play_pause.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.btn_play_pause.clicked.connect(self._toggle_timer)

        self.btn_finish_workout = QPushButton("Finish Workout")
        self.btn_finish_workout.setFixedSize(120, 40)
        self.btn_finish_workout.setStyleSheet("background-color: #9C27B0; color: white; font-weight: bold;")
        self.btn_finish_workout.clicked.connect(self._open_finalization_window)

        self.chk_mini_timer = QCheckBox("Mini Overlay")
        self.chk_mini_timer.setStyleSheet("color: #b0b0b0;")
        self.chk_mini_timer.toggled.connect(lambda checked: self.mini_timer.hide() if not checked else self.mini_timer.show())

        self.chk_voice = QCheckBox("Voice Prompts")
        self.chk_voice.setStyleSheet("color: #b0b0b0;")
        self.chk_voice.setChecked(True)

        checkboxes_layout = QVBoxLayout()
        checkboxes_layout.addWidget(self.chk_mini_timer)
        checkboxes_layout.addWidget(self.chk_voice)

        timer_layout.addWidget(self.btn_play_pause)
        timer_layout.addWidget(self.btn_finish_workout)
        timer_layout.addStretch()
        timer_layout.addWidget(self.lbl_timer)
        timer_layout.addStretch()
        timer_layout.addLayout(checkboxes_layout)
        layout.addLayout(timer_layout)

        self.rest_layout = QHBoxLayout()
        self.lbl_rest = QLabel("Resting...")
        self.lbl_rest.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.lbl_rest.setStyleSheet("color: #FF9800;")
        self.btn_add_time = QPushButton("+ 30s")
        self.btn_skip_rest = QPushButton("Skip Rest")
        self.btn_add_time.clicked.connect(lambda: self._add_rest_time(30))
        self.btn_skip_rest.clicked.connect(self._skip_rest)

        self.rest_layout.addStretch()
        self.rest_layout.addWidget(self.lbl_rest)
        self.rest_layout.addWidget(self.btn_add_time)
        self.rest_layout.addWidget(self.btn_skip_rest)
        self.rest_layout.addStretch()

        self.rest_container = QWidget()
        self.rest_container.setLayout(self.rest_layout)
        sp = self.rest_container.sizePolicy()
        sp.setRetainSizeWhenHidden(True)
        self.rest_container.setSizePolicy(sp)
        self.rest_container.hide()
        layout.addWidget(self.rest_container)

        info_layout = QHBoxLayout()
        text_layout = QVBoxLayout()

        self.btn_exit_preview = QPushButton("← Return to Active Set")
        self.btn_exit_preview.setStyleSheet("background-color: #F44336; color: white; font-weight: bold; padding: 5px; border-radius: 4px;")
        self.btn_exit_preview.clicked.connect(self._update_display)
        self.btn_exit_preview.hide()

        self.lbl_progress = QLabel("EXERCISE - OF -")
        self.lbl_progress.setStyleSheet("color: #888888; font-size: 14px; font-weight: bold; letter-spacing: 1px;")

        self.lbl_exercise_name = QLabel("Select a template...")
        self.lbl_exercise_name.setFont(QFont("Arial", 24, QFont.Weight.Bold))

        self.lbl_cues = QLabel()
        self.lbl_cues.setWordWrap(True)
        self.lbl_cues.setStyleSheet("color: #b0b0b0; font-style: italic; font-size: 15px;")

        self.barbell_visualizer = BarbellVisualizer()

        self.lbl_plate_math = QLabel()
        self.lbl_plate_math.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_plate_math.setStyleSheet("color: #FF9800; font-weight: bold; font-size: 14px; margin-bottom: 10px;")

        self.lbl_set_tracker = QLabel("-")

        text_layout.addWidget(self.btn_exit_preview)
        text_layout.addWidget(self.lbl_progress)
        text_layout.addWidget(self.lbl_exercise_name)
        text_layout.addWidget(self.lbl_cues)
        text_layout.addWidget(self.barbell_visualizer)
        text_layout.addWidget(self.lbl_plate_math)
        text_layout.addWidget(self.lbl_set_tracker)
        text_layout.addStretch()

        self.exercise_heatmap = AnatomicalHeatmap()

        info_layout.addLayout(text_layout)
        info_layout.addWidget(self.exercise_heatmap)
        info_layout.setStretch(0, 1)
        info_layout.setStretch(1, 1)
        layout.addLayout(info_layout)

        self.log_group = QGroupBox("Log Current Set")
        log_layout = QVBoxLayout()

        self.timed_set_widget = QWidget()
        ts_layout = QHBoxLayout(self.timed_set_widget)
        ts_layout.setContentsMargins(0, 0, 0, 0)

        self.btn_start_timed = QPushButton("▶ Start Set Timer")
        self.btn_start_timed.setStyleSheet("background-color: #9C27B0; color: white; font-weight: bold;")
        self.btn_start_timed.clicked.connect(self._toggle_timed_set)

        self.spin_buffer = QSpinBox()
        self.spin_buffer.setPrefix("Buffer: ")
        self.spin_buffer.setSuffix("s")
        self.spin_buffer.setValue(5)

        self.lbl_timed_status = QLabel("")

        ts_layout.addWidget(self.btn_start_timed)
        ts_layout.addWidget(self.spin_buffer)
        ts_layout.addWidget(self.lbl_timed_status)
        ts_layout.addStretch()

        log_layout.addWidget(self.timed_set_widget)
        self.timed_set_widget.hide()

        input_layout = QHBoxLayout()
        self.spin_weight = QDoubleSpinBox()
        self.spin_weight.setRange(0, 1000)
        self.spin_weight.setSuffix(" lbs")
        self.spin_weight.setSingleStep(2.5)
        self.spin_reps = QSpinBox()
        self.spin_reps.setRange(0, 1000)
        self.spin_reps.setSuffix(" reps")

        self.is_static_mode = False
        self.btn_toggle_static = QPushButton("⏱")
        self.btn_toggle_static.setToolTip("Toggle Reps / Time (s)")
        self.btn_toggle_static.setFixedWidth(40)
        self.btn_toggle_static.clicked.connect(self._toggle_static_mode)

        input_layout.addWidget(QLabel("Weight:"))
        input_layout.addWidget(self.spin_weight)
        input_layout.addWidget(QLabel("Target:"))
        input_layout.addWidget(self.spin_reps)

        self.chk_warmup = QCheckBox("Warm-Up Set")
        self.chk_warmup.setStyleSheet("color: #FF9800; font-weight: bold;")
        input_layout.addWidget(self.chk_warmup)

        self.btn_auto_warmup = QPushButton("Generate Warm-Ups")
        self.btn_auto_warmup.setStyleSheet("color: #FF9800; font-weight: bold;")
        self.btn_auto_warmup.clicked.connect(self._on_generate_warmups)
        input_layout.addWidget(self.btn_auto_warmup)

        log_layout.addLayout(input_layout)

        rpe_layout = QHBoxLayout()
        self.slider_rpe = QSlider(Qt.Orientation.Horizontal)
        self.slider_rpe.setRange(1, 10)
        self.slider_rpe.setValue(7)
        self.slider_rpe.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.lbl_rpe_val = QLabel("RPE: 7")
        self.slider_rpe.valueChanged.connect(self._on_rpe_changed)
        self._on_rpe_changed(7)

        self.txt_notes = QLineEdit()
        self.txt_notes.setPlaceholderText("Set Notes...")
        self.txt_notes.setStyleSheet("background: #2a2a2a; border: 1px solid #555; padding: 4px; border-radius: 4px;")

        rpe_layout.addWidget(QLabel("Effort:"))
        rpe_layout.addWidget(self.slider_rpe)
        rpe_layout.addWidget(self.lbl_rpe_val)
        rpe_layout.addWidget(self.txt_notes)
        log_layout.addLayout(rpe_layout)

        btn_layout = QHBoxLayout()
        self.btn_log = QPushButton("Complete Set")
        self.btn_log.setFixedSize(200, 40)
        self.btn_log.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
        self.btn_log.clicked.connect(self._on_log_set_clicked)
        self.btn_log.setEnabled(False)

        self.btn_skip_set = QPushButton("Skip Set")
        self.btn_skip_set.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold;")
        self.btn_skip_set.clicked.connect(self._on_skip_set_clicked)

        self.btn_undo = QPushButton("⟲ Undo Set")
        self.btn_undo.setStyleSheet("background-color: #555555; color: white;")
        self.btn_undo.clicked.connect(self._handle_undo_set)

        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_log)
        btn_layout.addWidget(self.btn_skip_set)
        btn_layout.addWidget(self.btn_undo)
        btn_layout.addStretch()
        log_layout.addLayout(btn_layout)
        self.log_group.setLayout(log_layout)
        layout.addWidget(self.log_group)

    def _on_rpe_changed(self, v):
        self.lbl_rpe_val.setText(f"RPE: {v}")
        if v <= 6: color = "#4CAF50" # Green
        elif v <= 8: color = "#FF9800" # Orange
        else: color = "#F44336" # Red
        self.lbl_rpe_val.setStyleSheet(f"color: {color}; font-weight: bold;")

    def _toggle_static_mode(self):
        self.is_static_mode = not self.is_static_mode
        if self.is_static_mode:
            self.spin_reps.setSuffix(" sec")
        else:
            self.spin_reps.setSuffix(" reps")

    def _setup_timers(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_clock)
        self.timer.start(1000)

    def _toggle_timer(self):
        self.controller.toggle_workout_state()
        if self.controller.is_active:
            self.btn_play_pause.setText("Pause Workout")
            self.btn_play_pause.setStyleSheet("background-color: #f44336; color: white; font-weight: bold;")
            if self.rest_seconds == 0:
                self.btn_log.setEnabled(True)
            self._update_display()
        else:
            self.btn_play_pause.setText("Resume Workout")
            self.btn_play_pause.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
            self.btn_log.setEnabled(False)

    def _update_clock(self):
        if not self.controller.is_active:
            return

        if self.active_set_state == SetState.BUFFER:
            self.buffer_remaining -= 1
            self.lbl_timed_status.setText(f"Get Ready: {self.buffer_remaining}s")
            self.lbl_timed_status.setStyleSheet("color: #FF9800; font-weight: bold;")
            if self.buffer_remaining <= 3 and self.buffer_remaining > 0:
                self._play_sound("tick")
            elif self.buffer_remaining <= 0:
                self._play_sound("bell")
                self.active_set_state = SetState.ACTIVE

        elif self.active_set_state == SetState.ACTIVE:
            self.set_time_remaining -= 1
            self.lbl_timed_status.setText(f"HOLD! {self.set_time_remaining}s left")
            self.lbl_timed_status.setStyleSheet("color: #4CAF50; font-weight: bold;")
            if self.set_time_remaining <= 3 and self.set_time_remaining > 0:
                self._play_sound("tick")
            elif self.set_time_remaining <= 0:
                self._play_sound("bell")
                self.announce("Target time reached.")
                self.lbl_timed_status.setText("Target Reached! Overtime: +0s")
                self.lbl_timed_status.setStyleSheet("color: #2196F3; font-weight: bold;")
                self.active_set_state = SetState.OVERTIME
                self.overtime_seconds = 0
                self.btn_start_timed.setText("⏹ Stop Timer")

        elif self.active_set_state == SetState.OVERTIME:
            self.overtime_seconds += 1
            self.lbl_timed_status.setText(f"Target Reached! Overtime: +{self.overtime_seconds}s")
            self.lbl_timed_status.setStyleSheet("color: #2196F3; font-weight: bold;")

        if self.controller.start_time:
            total_secs = int(time.time() - self.controller.start_time)
            t_mins, t_secs = divmod(total_secs, 60)
            global_str = f"Total Time: {t_mins:02d}:{t_secs:02d}"
        else:
            global_str = "Total Time: 00:00"

        if self.rest_seconds > 0:
            self.rest_seconds -= 1
            mins, secs = divmod(self.rest_seconds, 60)
            time_str = f"Resting: {mins:02d}:{secs:02d}"

            if self.chk_mini_timer.isChecked():
                if not self.mini_timer.isVisible(): self.mini_timer.show()
                self.mini_timer.set_display("Resting", time_str, True)

            self.lbl_timer.setText(time_str)
            self.lbl_timer.setStyleSheet("color: #FF9800;")
            self.global_timer_lbl.setText(f"{time_str}  |  {global_str}")
            self.global_timer_lbl.setStyleSheet("color: #FF9800; font-weight: bold; font-size: 16px;")

            if self.rest_seconds <= self.warning_threshold_sec and self.rest_seconds > 0:
                self._play_sound("tick")
            elif self.rest_seconds == 0:
                self._play_sound("bell")
                self._skip_rest()
        else:
            self.workout_seconds += 1
            mins, secs = divmod(self.workout_seconds, 60)
            time_str = f"Set Time: {mins:02d}:{secs:02d}"

            if self.chk_mini_timer.isChecked():
                if not self.mini_timer.isVisible(): self.mini_timer.show()
                task = self.controller.get_current_task()
                if task:
                    ex = task['exercise']
                    is_timed = ex.get('tracks_time', False)
                    tgt = f"Target: {task['target_reps']} {'s' if is_timed else 'reps'}"
                    self.mini_timer.set_display(f"{ex['name']} ({task['set_number']})", time_str, False, tgt)
                else:
                    self.mini_timer.set_display("Workout Complete", "00:00", False)
                    self.mini_timer.btn_action.setEnabled(False)

            self.lbl_timer.setText(time_str)
            self.lbl_timer.setStyleSheet("color: #4CAF50;")
            self.global_timer_lbl.setText(f"{time_str}  |  {global_str}")
            self.global_timer_lbl.setStyleSheet("color: #4CAF50; font-weight: bold; font-size: 16px;")

    def _add_rest_time(self, seconds: int): self.rest_seconds += seconds

    def _skip_rest(self):
        self.rest_seconds = 0
        self.workout_seconds = 0
        self.lbl_timer.setText("00:00")
        self.lbl_timer.setStyleSheet("color: #4CAF50;")
        self.rest_container.hide()
        self.btn_log.setEnabled(True)

    def _preview_exercise(self, index: int):
        if not self.controller.exercises or index >= len(self.controller.exercises): return

        ex = self.controller.exercises[index]
        is_bb = (ex.get('category') == 'Barbell')

        self.btn_exit_preview.show()
        self.log_group.setEnabled(False)

        self.lbl_progress.setText(f"PREVIEW: EXERCISE {index + 1} OF {len(self.controller.exercises)}")
        self.lbl_progress.setStyleSheet("color: #FF9800; font-size: 14px; font-weight: bold; letter-spacing: 1px;")
        self.lbl_exercise_name.setText(ex['name'])

        cues_text = ex.get('cues')
        if not cues_text: cues_text = "1. Focus on form\n2. Maintain tension\n3. Full range of motion"

        html_cues = "<ul style='margin-top: 0; margin-bottom: 0; padding-left: 20px;'>"
        for cue in cues_text.split('\n'):
            if cue.strip():
                clean_cue = cue.lstrip('0123456789. ')
                html_cues += f"<li>{clean_cue}</li>"
        html_cues += "</ul>"
        self.lbl_cues.setText(html_cues)

        self.lbl_set_tracker.setText("Preview Mode - Logging Disabled")

        loadout = PlateCalculator.calculate_loadout(ex['target_weight'], user_id=self.controller.current_user_id, is_barbell=is_bb, current_side_loadout=[])

        if loadout is not None:
            self.barbell_visualizer.set_loadout(loadout, is_barbell=is_bb)
            self.barbell_visualizer.show()

            counts = Counter(loadout[0]) if is_bb else Counter(loadout[1])
            parts = [f"{count}x{weight:g}" for weight, count in sorted(counts.items(), reverse=True)]
            math_str = ", ".join(parts) if parts else "Empty"
            prefix = "Load Per Side: " if is_bb else "Attach to Belt/Stack: "
            self.lbl_plate_math.setText(prefix + math_str)
        else:
            self.barbell_visualizer.hide()
            self.lbl_plate_math.setText("")

        volume_map = {}
        if ex.get('primary_muscle'): volume_map[ex['primary_muscle']] = 15
        if ex.get('secondary_muscles'):
            for sec in [s.strip() for s in ex['secondary_muscles'].split(',') if s.strip()]: volume_map[sec] = 5
        self.exercise_heatmap.update_heatmap(volume_map)

    def _update_display(self):
        task = self.controller.get_current_task()

        self._reset_timed_set()
        self.minimap.update_map(self.controller)

        self.btn_exit_preview.hide()
        self.log_group.setEnabled(True)
        self.lbl_progress.setStyleSheet("color: #888888; font-size: 14px; font-weight: bold; letter-spacing: 1px;")

        if not task:
            self.lbl_progress.setText("WORKOUT COMPLETE")
            self.lbl_exercise_name.setText("Workout Complete!")
            self.lbl_cues.setText("")
            self.lbl_plate_math.setText("")
            self.lbl_set_tracker.setText("-")
            self.btn_log.setEnabled(False)
            self.btn_play_pause.setEnabled(False)
            self.btn_auto_warmup.setEnabled(False)
            self.exercise_heatmap.update_heatmap({})
            self.timed_set_widget.hide()
            self._set_static_mode(False)
            return

        current_ex = task['exercise']
        current_set_num = task['set_number']
        is_emom = task.get('is_emom', False)
        is_warmup = task.get('is_warmup', False)

        if current_ex['name'] != self._last_exercise_name:
            self.txt_notes.clear()
            self._last_exercise_name = current_ex['name']

        idx = next((i for i, e in enumerate(self.controller.exercises) if e['name'] == current_ex['name']), 0)

        self.btn_auto_warmup.setEnabled(not is_warmup)
        self.btn_play_pause.setEnabled(True)

        if current_ex.get('tracks_time', False):
            self.timed_set_widget.show()
            self._set_static_mode(True)
        else:
            self.timed_set_widget.hide()
            self._set_static_mode(False)

        if is_emom and self.active_set_state == SetState.IDLE:
            if hasattr(self, 'announce'):
                self.announce(f"Starting E-MOM for {current_ex['name']}")
            self._toggle_timed_set()

        cues_text = current_ex.get('cues')
        if not cues_text:
             cues_text = "1. Focus on form\n2. Maintain tension\n3. Full range of motion"

        html_cues = "<ul style='margin-top: 0; margin-bottom: 0; padding-left: 20px;'>"
        for cue in cues_text.split('\n'):
            if cue.strip():
                clean_cue = cue.lstrip('0123456789. ')
                html_cues += f"<li>{clean_cue}</li>"
        html_cues += "</ul>"
        self.lbl_cues.setText(html_cues)

        total_ex = len(self.controller.exercises)
        self.lbl_progress.setText(f"EXERCISE {idx + 1} OF {total_ex}")
        self.lbl_exercise_name.setText(current_ex['name'])

        target_str = "Secs" if current_ex.get('tracks_time', False) else "Reps"
        self.lbl_set_tracker.setText(f"Set {current_set_num}  |  Target: {task['target_reps']} {target_str}")

        self.spin_weight.setValue(task['target_weight'])
        self.spin_reps.setValue(task['target_reps'])
        self.chk_warmup.setChecked(is_warmup)

        is_bb = (current_ex.get('category') == 'Barbell')
        loadout = PlateCalculator.calculate_loadout(task['target_weight'], user_id=self.controller.current_user_id, is_barbell=is_bb, current_side_loadout=self.current_left_loadout)

        if loadout is not None:
            self.current_left_loadout = loadout[0]
            self.barbell_visualizer.set_loadout(loadout, is_barbell=is_bb)
            self.barbell_visualizer.show()

            counts = Counter(loadout[0]) if is_bb else Counter(loadout[1])
            parts = [f"{count}x{weight:g}" for weight, count in sorted(counts.items(), reverse=True)]
            math_str = ", ".join(parts) if parts else "Empty"
            prefix = "Load Per Side: " if is_bb else "Attach to Belt/Stack: "
            self.lbl_plate_math.setText(prefix + math_str)
        else:
            self.current_left_loadout = []
            self.barbell_visualizer.hide()
            self.lbl_plate_math.setText("")

        volume_map = {}
        if current_ex.get('primary_muscle'): volume_map[current_ex['primary_muscle']] = 15
        if current_ex.get('secondary_muscles'):
            for sec in [s.strip() for s in current_ex['secondary_muscles'].split(',')]: volume_map[sec] = 5
        self.exercise_heatmap.update_heatmap(volume_map)

    def _on_generate_warmups(self):
        task = self.controller.get_current_task()
        if not task: return
        ex = task['exercise']
        is_bb = (ex.get('category') == 'Barbell')
        is_timed = ex.get('tracks_time', False)

        warmups = PlateCalculator.generate_warmup_sets(task['target_weight'], user_id=self.controller.current_user_id, is_barbell=is_bb)

        dialog = WarmupPreviewDialog(warmups, is_timed, self)
        if dialog.exec():
            final_warmups = dialog.get_warmups()
            self.controller.insert_warmups(final_warmups)
            self._update_display()

    def _on_skip_set_clicked(self):
        self.controller.skip_current_set()
        if not self.controller.get_current_task():
            self._open_finalization_window()
        else:
            self._update_display()

    def _on_log_set_clicked(self):
        self.btn_log.setEnabled(False)
        self._reset_timed_set()
        self.controller.log_set(
            reps=self.spin_reps.value(),
            weight=self.spin_weight.value(),
            rpe=self.slider_rpe.value(),
            is_warmup=self.chk_warmup.isChecked(),
            notes=self.txt_notes.text().strip()
        )
        self.slider_rpe.setValue(7)

        if not self.controller.get_current_task():
            self._open_finalization_window()
        else:
            self._update_display()
            rest_needed = self.controller.get_current_exercise().get('rest_seconds', 90)

            if rest_needed > 0:
                self.rest_seconds = rest_needed
                self.rest_container.show()
                next_task = self.controller.get_current_task()
                if next_task:
                    self.lbl_rest.setText(f"Resting... (Up Next: {next_task['exercise']['name']})")
                    self.announce(f"Rest started. Next up: {next_task['exercise']['name']}.")
            else:
                self._skip_rest()

    def _open_finalization_window(self):
        self.timer.stop()
        if not self.controller.session_logs:
            self.lbl_progress.setText("WORKOUT ABORTED")
            self.controller.is_active = False
            self.lbl_timer.setText("00:00")
            self._update_display()
            return

        dialog = WorkoutFinalizationDialog(self.controller.session_logs, self)
        if dialog.exec():
            self.controller.session_logs = dialog.get_final_logs()
            self._trigger_workout_review()
        else:
            self.timer.start(1000)

    def _trigger_workout_review(self):
        self.btn_undo.setEnabled(False)
        workout_data = self.controller.finish_workout()
        if not workout_data: return

        self.global_timer_lbl.setText("Workout Complete")
        self.global_timer_lbl.setStyleSheet("color: #888;")

        logs_by_ex = defaultdict(list)
        for log in workout_data['logs']: logs_by_ex[log['exercise']].append(log)

        engine = ProgressionEngine()
        suggestions = {}

        for ex_dict in self.controller.exercises:
            ex_name = ex_dict['name']
            if ex_name in logs_by_ex:
                is_bb = (ex_dict.get('category') == 'Barbell')
                eval_result = engine.evaluate_exercise_progression(
                    user_id=self.controller.current_user_id,
                    target_sets=ex_dict['target_sets'],
                    min_reps=ex_dict['target_reps_min'],
                    max_reps=ex_dict['target_reps_max'],
                    current_weight=ex_dict['target_weight'],
                    completed_logs=logs_by_ex[ex_name],
                    is_barbell=is_bb
                )
                suggestions[ex_name] = eval_result

        current_settings = {ex['name']: {'weight': ex['target_weight'], 'min_reps': ex['target_reps_min'], 'max_reps': ex['target_reps_max']} for ex in self.controller.exercises}
        dialog = WorkoutReviewDialog(workout_data['logs'], suggestions, current_settings, self)

        if dialog.exec():
            WorkoutDatabaseManager.update_routine_targets(self.combo_workout_selector.currentData(), dialog.get_final_targets())

        latest_bw = WorkoutDatabaseManager.get_latest_bodyweight(self.controller.current_user_id)
        workout_id = WorkoutDatabaseManager.save_completed_workout(
            user_id=self.controller.current_user_id,
            workout_name=self.combo_workout_selector.currentText(),
            duration_minutes=workout_data['duration_minutes'],
            bodyweight=latest_bw,
            logs=workout_data['logs']
        )
        self.controller.workout_id = workout_id

        worker = FitbitSyncWorker(workout_id, workout_data['duration_minutes'])
        QThreadPool.globalInstance().start(worker)

        event_bus.WORKOUT_COMPLETED.emit()
        self._update_display()

    def _handle_undo_set(self):
        if self.controller.undo_last_set():
            if not self.controller.is_active and self.btn_play_pause.text() == "Pause Workout":
                self.controller.is_active = True
                self.timer.start(1000)

            self.btn_log.setEnabled(True)

            self.workout_seconds = 0
            self.rest_seconds = 0
            self.lbl_timer.setText("00:00")
            self.lbl_timer.setStyleSheet("color: #4CAF50;")
            self.rest_container.hide()
            self._update_display()

    def _set_static_mode(self, is_static: bool):
        self.is_static_mode = is_static
        if self.is_static_mode:
            self.spin_reps.setSuffix(" sec")
        else:
            self.spin_reps.setSuffix(" reps")

    def _reset_timed_set(self):
        self.active_set_state = SetState.IDLE
        self.btn_start_timed.setText("▶ Start Set Timer")
        self.btn_start_timed.setStyleSheet("background-color: #9C27B0; color: white; font-weight: bold;")
        self.lbl_timed_status.setText("")

    def _toggle_timed_set(self):
        if self.active_set_state != SetState.IDLE:
            self._reset_timed_set()
        else:
            self.active_set_state = SetState.BUFFER
            self.buffer_remaining = self.spin_buffer.value()
            self.set_time_remaining = self.spin_reps.value()
            self.btn_start_timed.setText("⏹ Cancel Timer")
            self.btn_start_timed.setStyleSheet("background-color: #F44336; color: white; font-weight: bold;")