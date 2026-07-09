# ui/components/active_tracker.py
import os
import time
from collections import defaultdict
from enum import Enum, auto
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSpinBox, QDoubleSpinBox, QSlider,
    QGroupBox, QScrollArea, QComboBox, QCheckBox,
    QListWidget, QListWidgetItem
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

class MiniRestTimer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(140, 140)

        self.percentage = 1.0
        self.time_str = "00:00"
        self.oldPos = self.pos()

    def set_time(self, txt, percentage):
        self.time_str = txt
        self.percentage = max(0.0, min(1.0, percentage))
        self.update() # Triggers paintEvent to redraw the circle

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Inner transparent-ish black circle
        rect = QRectF(10, 10, self.width() - 20, self.height() - 20)
        painter.setPen(QPen(QColor(0, 0, 0, 150), 8))
        painter.setBrush(QColor(0, 0, 0, 180))
        painter.drawEllipse(rect)

        # Outer progress ring (Orange)
        painter.setPen(QPen(QColor("#FF9800"), 8, cap=Qt.PenCapStyle.RoundCap))
        start_angle = 90 * 16 # 12 o'clock position (PyQt angles are in 1/16ths of a degree)
        span_angle = int(-360 * self.percentage * 16) # Negative draws clockwise
        painter.drawArc(rect, start_angle, span_angle)

        # Timer Text
        painter.setPen(Qt.GlobalColor.white)
        painter.setFont(QFont("Arial", 28, QFont.Weight.Bold))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.time_str)

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

        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
        self.tray.show()

        self.mini_timer = MiniRestTimer()

        self.tts = QTextToSpeech()

        self._setup_audio()
        self._setup_ui()
        self._setup_timers()

    def announce(self, text: str):
        if self.audio_enabled and self.tts:
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

            self.rest_container.hide()
            self.log_group.setEnabled(True)
            self.btn_log.setEnabled(False) # Keep disabled until started

            self.controller.template_name = self.combo_workout_selector.currentText()
            self.controller.load_template(template_id)
            exercise_names = [ex['name'] for ex in self.controller.exercises]

            self.minimap.load_workout(exercise_names)
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

        timer_layout.addWidget(self.btn_play_pause)
        timer_layout.addStretch()
        timer_layout.addWidget(self.lbl_timer)
        timer_layout.addStretch()
        layout.addLayout(timer_layout)

        self.rest_layout = QHBoxLayout()
        self.lbl_rest = QLabel("Resting...")
        self.lbl_rest.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.lbl_rest.setStyleSheet("color: #FF9800;")
        self.btn_add_time = QPushButton("+ 30s")
        self.btn_skip_rest = QPushButton("Skip Rest")
        self.btn_add_time.clicked.connect(lambda: self._add_rest_time(30))
        self.btn_skip_rest.clicked.connect(self._skip_rest)
        self.chk_mini_timer = QCheckBox("Show Mini Overlay")
        self.chk_mini_timer.setStyleSheet("color: #b0b0b0;")
        self.chk_mini_timer.toggled.connect(lambda checked: self.mini_timer.hide() if not checked else None)

        self.rest_layout.addStretch()
        self.rest_layout.addWidget(self.chk_mini_timer)
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

        self.lbl_progress = QLabel("EXERCISE - OF -")
        self.lbl_progress.setStyleSheet("color: #888888; font-size: 14px; font-weight: bold; letter-spacing: 1px;")

        self.lbl_exercise_name = QLabel("Select a template...")
        self.lbl_exercise_name.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        self.barbell_visualizer = BarbellVisualizer()
        self.lbl_set_tracker = QLabel("-")

        self.cues_list = QListWidget()
        self.cues_list.setStyleSheet("background-color: transparent; border: none; color: #b0b0b0; font-style: italic;")
        self.cues_list.setMaximumHeight(80)

        text_layout.addWidget(self.lbl_progress)
        text_layout.addWidget(self.lbl_exercise_name)
        text_layout.addWidget(self.cues_list)
        text_layout.addWidget(self.barbell_visualizer )
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

        # --- TIMED SET WIDGET ---
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
        input_layout.addWidget(QLabel("Reps:"))
        input_layout.addWidget(self.spin_reps)

        self.chk_warmup = QCheckBox("Warm-Up Set")
        self.chk_warmup.setStyleSheet("color: #FF9800; font-weight: bold;")
        input_layout.addWidget(self.chk_warmup)

        self.btn_auto_warmup = QPushButton("Auto Warm-Up")
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
        self.slider_rpe.valueChanged.connect(lambda v: self.lbl_rpe_val.setText(f"RPE: {v}"))

        rpe_layout.addWidget(QLabel("Effort:"))
        rpe_layout.addWidget(self.slider_rpe)
        rpe_layout.addWidget(self.lbl_rpe_val)
        log_layout.addLayout(rpe_layout)

        btn_layout = QHBoxLayout()
        self.btn_log = QPushButton("Complete Set")
        self.btn_log.setFixedSize(200, 40)
        self.btn_log.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
        self.btn_log.clicked.connect(self._on_log_set_clicked)
        self.btn_log.setEnabled(False)

        self.btn_undo = QPushButton("⟲ Undo Set")
        self.btn_undo.setStyleSheet("background-color: #555555; color: white;")
        self.btn_undo.clicked.connect(self._handle_undo_set)

        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_log)
        btn_layout.addWidget(self.btn_undo)
        btn_layout.addStretch()
        log_layout.addLayout(btn_layout)
        self.log_group.setLayout(log_layout)
        layout.addWidget(self.log_group)

        history_box = QGroupBox("Completed Sets History")
        self.history_layout = QVBoxLayout()
        self.history_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        history_box.setLayout(self.history_layout)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(history_box)
        scroll.setMaximumHeight(150)
        layout.addWidget(scroll)

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
            self.btn_log.setEnabled(True)
            self._update_display()
        else:
            self.btn_play_pause.setText("Resume Workout")
            self.btn_play_pause.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
            self.btn_log.setEnabled(False)

    def _update_clock(self):
        if not self.controller.is_active:
            return

        if self.active_set_state == "BUFFER":
            self.buffer_remaining -= 1
            self.lbl_timed_status.setText(f"Get Ready: {self.buffer_remaining}s")
            self.lbl_timed_status.setStyleSheet("color: #FF9800; font-weight: bold;")
            if self.buffer_remaining <= 3 and self.buffer_remaining > 0:
                self._play_sound("tick")
            elif self.buffer_remaining <= 0:
                self._play_sound("bell")
                self.active_set_state = "ACTIVE"
        elif self.active_set_state == "ACTIVE":
            self.set_time_remaining -= 1
            self.lbl_timed_status.setText(f"HOLD! {self.set_time_remaining}s left")
            self.lbl_timed_status.setStyleSheet("color: #4CAF50; font-weight: bold;")
            if self.set_time_remaining <= 3 and self.set_time_remaining > 0:
                self._play_sound("tick")
            elif self.set_time_remaining <= 0:
                self._play_sound("bell")
                self.lbl_timed_status.setText("Time's Up! Log your time.")
                self.lbl_timed_status.setStyleSheet("color: #2196F3; font-weight: bold;")
                self.active_set_state = "IDLE"
                self.btn_start_timed.setText("▶ Restart Timer")
                self.btn_start_timed.setStyleSheet("background-color: #9C27B0; color: white; font-weight: bold;")

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

            # --- PROGRESS PERCENTAGE CALCULATION ---
            current_ex = self.controller.get_current_exercise()
            total_rest_target = current_ex.get('rest_seconds', 90) if current_ex else 90
            pct = self.rest_seconds / total_rest_target if total_rest_target > 0 else 0.0

            if self.chk_mini_timer.isChecked():
                if not self.mini_timer.isVisible(): self.mini_timer.show()
                self.mini_timer.set_time(f"{mins:02d}:{secs:02d}", pct)

            self.lbl_timer.setText(time_str)
            self.lbl_timer.setStyleSheet("color: #FF9800;")

            self.global_timer_lbl.setText(f"{time_str}  |  {global_str}")
            self.global_timer_lbl.setStyleSheet("color: #FF9800; font-weight: bold; font-size: 16px;")

            if self.rest_seconds == self.warning_threshold_sec:
                self._play_sound("tick")
            elif self.rest_seconds < self.warning_threshold_sec and self.rest_seconds > 0:
                self._play_sound("tick")
            elif self.rest_seconds == 0:
                self._play_sound("bell")
                self.tray.showMessage("Rest Complete!", "Time for your next set.", QSystemTrayIcon.MessageIcon.Information, 3000)
                self._skip_rest()

                next_task = self.controller.get_current_task()
                if next_task:
                    ex_name = next_task['exercise']['name']
                    self.announce(f"Time is up. Next exercise: {ex_name}")
        else:
            self.mini_timer.hide()
            self.workout_seconds += 1
            mins, secs = divmod(self.workout_seconds, 60)
            time_str = f"Set Time: {mins:02d}:{secs:02d}"

            # Update Local Timer
            self.lbl_timer.setText(time_str)
            self.lbl_timer.setStyleSheet("color: #4CAF50;")

            # Update Global Header
            self.global_timer_lbl.setText(f"{time_str}  |  {global_str}")
            self.global_timer_lbl.setStyleSheet("color: #4CAF50; font-weight: bold; font-size: 16px;")

    def _add_rest_time(self, seconds: int): self.rest_seconds += seconds

    def _skip_rest(self):
        self.rest_seconds = 0
        self.workout_seconds = 0
        self.rest_container.hide()
        self.log_group.setEnabled(True)
        self.lbl_timer.setText("00:00")
        self.lbl_timer.setStyleSheet("color: #4CAF50;")

    def _update_display(self):
        # 1. Ask the queue for the exact set we are currently on
        task = self.controller.get_current_task()

        # 2. Clear out the history UI logs from the previously viewed set
        for i in reversed(range(self.history_layout.count())):
            widget = self.history_layout.itemAt(i).widget()
            if widget: widget.setParent(None)

        self._reset_timed_set()

        # 3. Handle Workout Completion State
        if not task:
            self.lbl_progress.setText("WORKOUT COMPLETE")
            self.lbl_exercise_name.setText("Workout Complete!")
            self.lbl_set_tracker.setText("-")
            self.btn_log.setEnabled(False)
            self.btn_play_pause.setEnabled(False)
            self.btn_auto_warmup.setEnabled(False)
            self.exercise_heatmap.update_heatmap({})
            self.timed_set_widget.hide()
            self._set_static_mode(False)
            return

        # 4. Extract data from the unrolled task
        current_ex = task['exercise']
        current_set_num = task['set_number']
        is_emom = task.get('is_emom', False)

        # Update Minimap based on unique exercise index
        idx = next((i for i, e in enumerate(self.controller.exercises) if e['name'] == current_ex['name']), 0)
        self.minimap.set_active_node(idx)

        self.btn_auto_warmup.setEnabled(True)
        self.btn_play_pause.setEnabled(True)

        # 5. Handle UI toggles for Timed vs Rep-based exercises
        if current_ex.get('tracks_time', False):
            self.timed_set_widget.show()
            self._set_static_mode(True)
        else:
            self.timed_set_widget.hide()
            self._set_static_mode(False)

        # 6. Announce starting an EMOM automatically
        if is_emom and self.active_set_state == SetState.IDLE:
            if hasattr(self, 'announce'):
                self.announce(f"Starting E-MOM for {current_ex['name']}")
            self._toggle_timed_set() # Auto-start the timer for EMOMs!

        # 7. Update Text UI elements
        cues_text = current_ex.get('cues')
        if not cues_text:
             cues_text = "1. Focus on form\n2. Maintain tension\n3. Full range of motion"

        self.cues_list.clear()
        for cue in cues_text.split('\n'):
            self.cues_list.addItem(QListWidgetItem(cue))

        total_ex = len(self.controller.exercises)
        self.lbl_progress.setText(f"EXERCISE {idx + 1} OF {total_ex}")
        self.lbl_exercise_name.setText(current_ex['name'])

        target_str = "Secs" if current_ex.get('tracks_time', False) else "Reps"
        self.lbl_set_tracker.setText(f"Set {current_set_num} of {current_ex['target_sets']}  |  Target: {current_ex['target_reps_min']} - {current_ex['target_reps_max']} {target_str}")

        self.spin_weight.setValue(current_ex['target_weight'])
        self.spin_reps.setValue(current_ex['target_reps_max'])
        self.chk_warmup.setChecked(False)

        # 8. Render Visualizers
        loadout = PlateCalculator.calculate_loadout(current_ex['target_weight'], user_id=self.controller.current_user_id)
        if loadout is not None:
            self.barbell_visualizer.set_loadout(loadout)
            self.barbell_visualizer.show()
        else:
            self.barbell_visualizer.hide()

        volume_map = {}
        if current_ex.get('primary_muscle'): volume_map[current_ex['primary_muscle']] = 15
        if current_ex.get('secondary_muscles'):
            for sec in [s.strip() for s in current_ex['secondary_muscles'].split(',')]: volume_map[sec] = 5
        self.exercise_heatmap.update_heatmap(volume_map)

        # 9. Load Historical Context for THIS specific exercise
        for log in self.controller.session_logs:
            if log['exercise'] == current_ex['name']:
                color = "#888888" if log.get('is_warmup') else ("#4CAF50" if log['reps'] >= current_ex['target_reps_min'] else "#F44336")
                prefix = "Warmup" if log.get('is_warmup') else f"Set {log['set']}"
                rep_type = "s" if current_ex.get('tracks_time', False) else " reps"

                lbl = QLabel(f"{prefix}: {log['reps']}{rep_type} @ {log['weight']} lbs | RPE: {log['rpe']}")
                lbl.setStyleSheet(f"color: {color}; font-weight: bold; padding: 2px;")
                self.history_layout.addWidget(lbl)

    def _on_generate_warmups(self):
        current_ex = self.controller.get_current_exercise()
        if not current_ex: return
        warmups = PlateCalculator.generate_warmup_sets(current_ex['target_weight'], user_id=self.controller.current_user_id)
        for w in warmups:
            self.controller.log_set(reps=w['reps'], weight=w['weight'], rpe=5, is_warmup=True)
        self._update_display()

    def _on_log_set_clicked(self):
        self._reset_timed_set()
        self.controller.log_set(
            reps=self.spin_reps.value(),
            weight=self.spin_weight.value(),
            rpe=self.slider_rpe.value(),
            is_warmup=self.chk_warmup.isChecked()
        )
        self.slider_rpe.setValue(7)

        if self.controller.current_exercise_index >= len(self.controller.exercises):
            self._trigger_workout_review()
        else:
            self._update_display()
            rest_needed = self.controller.get_current_exercise().get('rest_seconds', 90)

            # If the exercise has 0 rest, skip the rest UI immediately to reset the set timer
            if rest_needed > 0:
                self.rest_seconds = rest_needed
                self.rest_container.show()
                self.log_group.setEnabled(False)
            else:
                self._skip_rest()

    def _trigger_workout_review(self):
        self.timer.stop()
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
                eval_result = engine.evaluate_exercise_progression(
                    user_id=self.controller.current_user_id,
                    target_sets=ex_dict['target_sets'],
                    min_reps=ex_dict['target_reps_min'],
                    max_reps=ex_dict['target_reps_max'],
                    current_weight=ex_dict['target_weight'],
                    completed_logs=logs_by_ex[ex_name]
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

        # Fire signal to prompt updates
        event_bus.WORKOUT_COMPLETED.emit()
        self._update_display()

    def _handle_undo_set(self):
        if self.controller.undo_last_set():
            if not self.controller.is_active and self.btn_play_pause.text() == "Pause Workout":
                self.controller.is_active = True
                self.timer.start(1000)
            if hasattr(self, 'btn_log'):
                self.btn_log.setEnabled(True)

            self.workout_seconds = 0  # <--- Reset the set timer so you can re-attempt cleanly
            self.rest_container.hide()
            self.log_group.setEnabled(True)
            self._update_display()

    def _set_static_mode(self, is_static: bool):
        self.is_static_mode = is_static
        if self.is_static_mode:
            self.spin_reps.setSuffix(" sec")
        else:
            self.spin_reps.setSuffix(" reps")

    def _reset_timed_set(self):
        self.active_set_state = "IDLE"
        self.btn_start_timed.setText("▶ Start Set Timer")
        self.btn_start_timed.setStyleSheet("background-color: #9C27B0; color: white; font-weight: bold;")
        self.lbl_timed_status.setText("")

    def _toggle_timed_set(self):
        if self.active_set_state != "IDLE":
            self._reset_timed_set()
        else:
            self.active_set_state = "BUFFER"
            self.buffer_remaining = self.spin_buffer.value()
            self.set_time_remaining = self.spin_reps.value()
            self.btn_start_timed.setText("⏹ Cancel Timer")
            self.btn_start_timed.setStyleSheet("background-color: #F44336; color: white; font-weight: bold;")