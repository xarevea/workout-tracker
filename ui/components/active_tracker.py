# ui/components/active_tracker.py
import os
from collections import defaultdict
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QSpinBox, QDoubleSpinBox, QSlider, 
    QGroupBox, QScrollArea, QComboBox, QCheckBox,
    QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt, QTimer, QUrl, QThreadPool
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtMultimedia import QSoundEffect
from PyQt6.QtWidgets import QSystemTrayIcon, QStyle

from ui.components.body_heatmap import AnatomicalHeatmap
from ui.components.review_dialog import WorkoutReviewDialog
from modules.equipment.plate_calculator import PlateCalculator
from core.db_operations import WorkoutDatabaseManager
from core.events import event_bus
from modules.progression.engine import ProgressionEngine
from modules.workout.session import FitbitSyncWorker

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
        
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
        self.tray.show()
        
        self._setup_audio()
        self._setup_ui()
        self._setup_timers()

    def refresh_data(self):
        if self.controller.is_active: return 

        self.combo_workout_selector.blockSignals(True)
        self.combo_workout_selector.clear()
        
        templates = WorkoutDatabaseManager.get_all_templates()
        for t in templates:
            self.combo_workout_selector.addItem(t['name'], userData=t['id'])
        self.combo_workout_selector.blockSignals(False)

        if self.combo_workout_selector.count() > 0:
            self._load_selected_workout()

    def _load_selected_workout(self):
        template_id = self.combo_workout_selector.currentData()
        if template_id:
            if self.controller.is_active:
                self._toggle_timer() 
                
            self.workout_seconds = 0
            self.rest_seconds = 0
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
        
        self.lbl_progress = QLabel("EXERCISE - OF -")
        self.lbl_progress.setStyleSheet("color: #888888; font-size: 14px; font-weight: bold; letter-spacing: 1px;")
        
        self.lbl_exercise_name = QLabel("Select a template...")
        self.lbl_exercise_name.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        self.lbl_loadout = QLabel("") 
        self.lbl_loadout.setStyleSheet("color: #2196F3; font-weight: bold;")
        self.lbl_set_tracker = QLabel("-")

        self.cues_list = QListWidget()
        self.cues_list.setStyleSheet("background-color: transparent; border: none; color: #b0b0b0; font-style: italic;")
        self.cues_list.setMaximumHeight(80)
        
        text_layout.addWidget(self.lbl_progress)
        text_layout.addWidget(self.lbl_exercise_name)
        text_layout.addWidget(self.cues_list)
        text_layout.addWidget(self.lbl_loadout)
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
        input_layout = QHBoxLayout()
        self.spin_weight = QDoubleSpinBox()
        self.spin_weight.setRange(0, 1000)
        self.spin_weight.setSuffix(" lbs")
        self.spin_weight.setSingleStep(2.5)
        self.spin_reps = QSpinBox()
        self.spin_reps.setRange(0, 100)
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
        if not self.controller.is_active: return
        if self.rest_seconds > 0:
            self.rest_seconds -= 1
            mins, secs = divmod(self.rest_seconds, 60)
            time_str = f"Resting: {mins:02d}:{secs:02d}"
            self.lbl_timer.setText(time_str)
            self.lbl_timer.setStyleSheet("color: #FF9800;")
            self.global_timer_lbl.setText(time_str)
            self.global_timer_lbl.setStyleSheet("color: #FF9800; font-weight: bold; font-size: 18px;")
            
            if self.rest_seconds == self.warning_threshold_sec: self._play_sound("tick")
            elif self.rest_seconds < self.warning_threshold_sec and self.rest_seconds > 0: self._play_sound("tick")
            elif self.rest_seconds == 0:
                self._play_sound("bell")
                self.tray.showMessage("Rest Complete!", "Time for your next set.", QSystemTrayIcon.MessageIcon.Information, 3000)
                self._skip_rest() 
        else:
            self.workout_seconds += 1
            mins, secs = divmod(self.workout_seconds, 60)
            time_str = f"Active: {mins:02d}:{secs:02d}"

            self.lbl_timer.setText(time_str)
            self.lbl_timer.setStyleSheet("color: #4CAF50;")
            self.global_timer_lbl.setText(time_str)
            self.global_timer_lbl.setStyleSheet("color: #4CAF50; font-weight: bold; font-size: 18px;")

    def _add_rest_time(self, seconds: int): self.rest_seconds += seconds

    def _skip_rest(self):
        self.rest_seconds = 0
        self.rest_container.hide()
        self.log_group.setEnabled(True)
        self.lbl_timer.setText("00:00")
        self.lbl_timer.setStyleSheet("color: #4CAF50;")

    def _update_display(self):
        current_ex = self.controller.get_current_exercise()
        self.minimap.set_active_node(self.controller.current_exercise_index)
        for i in reversed(range(self.history_layout.count())): 
            widget = self.history_layout.itemAt(i).widget()
            if widget: widget.setParent(None)

        if not current_ex:
            self.lbl_progress.setText("WORKOUT COMPLETE")
            self.lbl_exercise_name.setText("Workout Complete!")
            self.lbl_loadout.setText("")
            self.lbl_set_tracker.setText("-")
            self.btn_log.setEnabled(False)
            self.btn_play_pause.setEnabled(False)
            self.btn_auto_warmup.setEnabled(False)
            self.exercise_heatmap.update_heatmap({}) 
            return
            
        self.btn_auto_warmup.setEnabled(True)
        self.btn_play_pause.setEnabled(True)

        cues_text = current_ex.get('cues')
        if not cues_text:
             cues_text = "1. Focus on form\n2. Maintain tension\n3. Full range of motion"
             
        self.cues_list.clear()
        for cue in cues_text.split('\n'):
            self.cues_list.addItem(QListWidgetItem(cue))

        total_ex = len(self.controller.exercises)
        current_idx = self.controller.current_exercise_index + 1
        self.lbl_progress.setText(f"EXERCISE {current_idx} OF {total_ex}")

        self.lbl_exercise_name.setText(current_ex['name'])
        self.lbl_set_tracker.setText(f"Set {self.controller.current_set} of {current_ex['target_sets']}  |  Target: {current_ex['target_reps_min']} - {current_ex['target_reps_max']} Reps")
        
        self.spin_weight.setValue(current_ex['target_weight'])
        self.spin_reps.setValue(current_ex['target_reps_max'])
        
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
    
    def _on_generate_warmups(self):
        current_ex = self.controller.get_current_exercise()
        if not current_ex: return
        warmups = PlateCalculator.generate_warmup_sets(current_ex['target_weight'])
        for w in warmups:
            self.controller.log_set(reps=w['reps'], weight=w['weight'], rpe=5, is_warmup=True)
        self._update_display()
    
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
        event_bus.workout_completed.emit()
        self._update_display()

    def _handle_undo_set(self):
        if self.controller.undo_last_set():
            if not self.controller.is_active and self.btn_play_pause.text() == "Pause Workout":
                self.controller.is_active = True
                self.timer.start(1000)
            if hasattr(self, 'btn_log'):
                self.btn_log.setEnabled(True)
            self.rest_container.hide()
            self.log_group.setEnabled(True)
            self._update_display()