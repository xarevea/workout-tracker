import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QSpinBox, QDoubleSpinBox, QSlider, QGroupBox, QScrollArea, QComboBox, QCheckBox
)
from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtMultimedia import QSoundEffect
from PyQt6.QtWidgets import QSystemTrayIcon, QStyle

from ui.components.body_heatmap import AnatomicalHeatmap
from core.database import get_connection
from modules.equipment.plate_calculator import PlateCalculator
from ui.components.review_dialog import WorkoutReviewDialog
from core.db_operations import WorkoutDatabaseManager
from core.events import event_bus

class ActiveTrackerWidget(QWidget):
    def __init__(self, controller, minimap, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.minimap = minimap
        
        self.workout_seconds = 0
        self.rest_seconds = 0
        self.audio_enabled = True
        self.warning_threshold_sec = 5 
        
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
        self.tray.show()
        
        self._setup_audio()
        self._setup_ui()
        self._setup_timers()

    def refresh_data(self):
        """Loads available active templates to select from."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM routine_templates WHERE is_active=1")
        templates = cursor.fetchall()
        conn.close()

        self.combo_workout_selector.blockSignals(True)
        self.combo_workout_selector.clear()
        
        for t in templates:
            self.combo_workout_selector.addItem(t['name'], userData=t['id'])
            
        self.combo_workout_selector.blockSignals(False)
        
        if templates:
            self._load_selected_workout()

    def _load_selected_workout(self):
        template_id = self.combo_workout_selector.currentData()
        if template_id:
            # 1. Safety Reset: Pause and zero-out timers if switching templates
            if self.controller.is_active:
                self._toggle_timer() # Pauses the active workout
                
            self.workout_seconds = 0
            self.rest_seconds = 0
            self.lbl_timer.setText("00:00")
            self.lbl_timer.setStyleSheet("color: white;")
            
            # Hide rest UI and re-enable logging
            self.rest_container.hide()
            self.log_group.setEnabled(True)
            
            # 2. Load the new data
            self.controller.load_template(template_id)
            exercise_names = [ex['name'] for ex in self.controller.exercises]
            
            # 3. Update the UI
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

        # --- WORKOUT SELECTOR ---
        workout_select_layout = QHBoxLayout()
        self.combo_workout_selector = QComboBox()
        self.combo_workout_selector.currentIndexChanged.connect(self._load_selected_workout)
        workout_select_layout.addWidget(QLabel("Today's Workout:"))
        workout_select_layout.addWidget(self.combo_workout_selector, stretch=1)
        layout.addLayout(workout_select_layout)

        # --- TIMERS & CONTROLS ---
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

        # --- REST CONTROLS ---
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
        self.rest_container.hide()
        layout.addWidget(self.rest_container)

        # --- EXERCISE INFO & HEATMAP ---
        info_layout = QHBoxLayout()
        text_layout = QVBoxLayout()
        self.lbl_exercise_name = QLabel("Select a template...")
        self.lbl_exercise_name.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        self.lbl_loadout = QLabel("") # NEW: Plate Loadout
        self.lbl_loadout.setStyleSheet("color: #2196F3; font-weight: bold;")
        self.lbl_set_tracker = QLabel("-")
        text_layout.addWidget(self.lbl_exercise_name)
        text_layout.addWidget(self.lbl_loadout)
        text_layout.addWidget(self.lbl_set_tracker)
        
        self.exercise_heatmap = AnatomicalHeatmap()
        self.exercise_heatmap.setFixedSize(300, 200) # Compact heatmap
        
        info_layout.addLayout(text_layout)
        info_layout.addWidget(self.exercise_heatmap)
        layout.addLayout(info_layout)

        # --- LOGGING AREA ---
        self.log_group = QGroupBox("Log Current Set")
        log_layout = QVBoxLayout()
        input_layout = QHBoxLayout()
        self.spin_weight = QDoubleSpinBox()
        self.spin_weight.setRange(0, 1000)
        self.spin_weight.setSuffix(" lbs")
        self.spin_weight.setSingleStep(2.5)
        self.spin_reps = QSpinBox()
        self.spin_reps.setRange(0, 100)
        self.spin_reps.setSuffix(" reps")

        input_layout.addWidget(QLabel("Weight:"))
        input_layout.addWidget(self.spin_weight)
        input_layout.addWidget(QLabel("Reps:"))
        input_layout.addWidget(self.spin_reps)

        self.chk_warmup = QCheckBox("Warm-Up Set")
        self.chk_warmup.setStyleSheet("color: #FF9800; font-weight: bold;")
        input_layout.addWidget(self.chk_warmup)

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
        self.btn_log = QPushButton("Log Set & Start Rest")
        self.btn_log.setFixedSize(200, 40)
        self.btn_log.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
        self.btn_log.clicked.connect(self._on_log_set_clicked)
        self.btn_log.setEnabled(False) 
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_log)
        btn_layout.addStretch()
        log_layout.addLayout(btn_layout)
        self.log_group.setLayout(log_layout)
        layout.addWidget(self.log_group)

        # History
        history_box = QGroupBox("Completed Sets History")
        self.history_layout = QVBoxLayout()
        self.history_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        history_box.setLayout(self.history_layout)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(history_box)
        scroll.setMaximumHeight(150)
        layout.addWidget(scroll)

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
        if not self.controller.is_active: return
        if self.rest_seconds > 0:
            self.rest_seconds -= 1
            mins, secs = divmod(self.rest_seconds, 60)
            self.lbl_timer.setText(f"{mins:02d}:{secs:02d}")
            self.lbl_timer.setStyleSheet("color: #FF9800;")
            
            if self.rest_seconds == self.warning_threshold_sec: self._play_sound("tick")
            elif self.rest_seconds < self.warning_threshold_sec and self.rest_seconds > 0: self._play_sound("tick")
            elif self.rest_seconds == 0:
                self._play_sound("bell")
                self.tray.showMessage("Rest Complete!", "Time for your next set.", QSystemTrayIcon.MessageIcon.Information, 3000)
                self._skip_rest() 
        else:
            self.workout_seconds += 1
            mins, secs = divmod(self.workout_seconds, 60)
            self.lbl_timer.setText(f"{mins:02d}:{secs:02d}")
            self.lbl_timer.setStyleSheet("color: #4CAF50;")

    def _add_rest_time(self, seconds: int): self.rest_seconds += seconds

    def _skip_rest(self):
        self.rest_seconds = 0
        self.workout_seconds = 0 # ZERO OUT THE SET TIMER
        self.rest_container.hide()
        self.log_group.setEnabled(True)
        self.lbl_timer.setText("00:00")
        self.lbl_timer.setStyleSheet("color: #4CAF50;")

    def _update_display(self):
        current_ex = self.controller.get_current_exercise()
        for i in reversed(range(self.history_layout.count())): 
            widget = self.history_layout.itemAt(i).widget()
            if widget: widget.setParent(None)

        if not current_ex:
            self.lbl_exercise_name.setText("Workout Complete!")
            self.lbl_loadout.setText("")
            self.lbl_set_tracker.setText("-")
            self.btn_log.setEnabled(False)
            self.btn_play_pause.setEnabled(False)
            self.exercise_heatmap.update_heatmap({}) 
            return

        self.lbl_exercise_name.setText(current_ex['name'])
        self.lbl_set_tracker.setText(f"Set {self.controller.current_set} of {current_ex['target_sets']}")
        
        self.spin_weight.setValue(current_ex['target_weight'])
        self.spin_reps.setValue(current_ex['target_reps_max']) # FIXED
        self.minimap.set_active_node(self.controller.current_exercise_index)
        self.chk_warmup.setChecked(False) 

        loadout = PlateCalculator.calculate_loadout(current_ex['target_weight'])
        if loadout is not None and len(loadout) > 0:
            self.lbl_loadout.setText(f"Loadout per side: [ {' | '.join([f'{p}lb' for p in loadout])} ]")
        else:
            self.lbl_loadout.setText("")

        volume_map = {}
        if current_ex.get('primary_muscle'): volume_map[current_ex['primary_muscle']] = 15 
        if current_ex.get('secondary_muscles'):
            for sec in [s.strip() for s in current_ex['secondary_muscles'].split(',')]: volume_map[sec] = 5 
        self.exercise_heatmap.update_heatmap(volume_map)

        for log in self.controller.session_logs:
            if log['exercise'] == current_ex['name']:
                color = "#888888" if log.get('is_warmup') else ("#4CAF50" if log['reps'] >= current_ex['target_reps_min'] else "#F44336")
                prefix = "Warmup" if log.get('is_warmup') else f"Set {log['set']}"
                lbl = QLabel(f"{prefix}: {log['reps']} reps @ {log['weight']} lbs | RPE: {log['rpe']}")
                lbl.setStyleSheet(f"color: {color}; font-weight: bold; padding: 2px;")
                self.history_layout.addWidget(lbl)
    
    def _on_log_set_clicked(self):
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
            self.rest_seconds = self.controller.get_current_exercise().get('rest_seconds', 90)
            self.rest_container.show()
            self.log_group.setEnabled(False)

    def _trigger_workout_review(self):
        self.timer.stop()
        workout_data = self.controller.finish_workout()
        
        from collections import defaultdict
        logs_by_ex = defaultdict(list)
        for log in workout_data['logs']: logs_by_ex[log['exercise']].append(log)
            
        from modules.progression.engine import ProgressionEngine
        engine = ProgressionEngine()
        suggestions = {}
        
        for ex_dict in self.controller.exercises:
            ex_name = ex_dict['name']
            if ex_name in logs_by_ex:
                eval_result = engine.evaluate_exercise_progression(
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
            
        WorkoutDatabaseManager.save_completed_workout(
            workout_name=self.combo_workout_selector.currentText(),
            duration_minutes=workout_data['duration_minutes'],
            bodyweight=185.0,
            logs=workout_data['logs']
        )
        
        event_bus.workout_completed.emit() # Triggers dashboard update
        self.lbl_exercise_name.setText("Workout Complete!")