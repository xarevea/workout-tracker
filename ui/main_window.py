# ui/main_window.py
import qtawesome as qta
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QStackedWidget, QLabel, QSystemTrayIcon, QMenu,
    QComboBox, QInputDialog, QMessageBox, QGraphicsOpacityEffect
)
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtCore import Qt, QPropertyAnimation, QAbstractAnimation

from core.db_operations import WorkoutDatabaseManager
from core.events import event_bus
from modules.workout.session import WorkoutSessionController
from ui.components.active_tracker import ActiveTrackerWidget
from ui.components.minimap import WorkoutMinimap
from ui.views.base_view import BaseView
from ui.views.bodyweight_hub import BodyweightHubView
from ui.views.clinical_analytics import ClinicalAnalyticsView
from ui.views.dashboard import DashboardView
from ui.views.equipment import EquipmentView
from ui.views.exercise_dictionary import ExerciseDictionaryView
from ui.views.history import WorkoutHistoryView
from ui.views.program_sandbox import ProgramSandboxView
from ui.views.settings import SettingsView
from utils.gui_utils import add_button_above_stretch, create_sidebar_button

class FadingStackedWidget(QStackedWidget):
    """A polished Stacked Widget that fades between views."""
    def setCurrentIndex(self, index):
        if index == self.currentIndex(): return

        self.fade_out = QGraphicsOpacityEffect(self)
        self.currentWidget().setGraphicsEffect(self.fade_out)

        self.anim_out = QPropertyAnimation(self.fade_out, b"opacity")
        self.anim_out.setDuration(100)
        self.anim_out.setStartValue(1.0)
        self.anim_out.setEndValue(0.0)

        self.anim_out.finished.connect(lambda: self._on_fade_out_done(index))
        self.anim_out.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)

    def _on_fade_out_done(self, index):
        super().setCurrentIndex(index)

        self.fade_in = QGraphicsOpacityEffect(self)
        self.currentWidget().setGraphicsEffect(self.fade_in)

        self.anim_in = QPropertyAnimation(self.fade_in, b"opacity")
        self.anim_in.setDuration(150)
        self.anim_in.setStartValue(0.0)
        self.anim_in.setEndValue(1.0)
        self.anim_in.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)

class WorkoutContainer(BaseView):
    def __init__(self, minimap, active_tracker, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(minimap, stretch=1)
        layout.addWidget(active_tracker, stretch=3)
        self.active_tracker = active_tracker

    def refresh_data(self):
        self.active_tracker.current_user_id = self.current_user_id
        self.active_tracker.current_program_id = self.current_program_id
        self.active_tracker.refresh_data()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hybrid Tracker")
        self.resize(1100, 700)

        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_ComputerIcon))

        tray_menu = QMenu()
        restore_action = QAction("Restore", self)
        restore_action.triggered.connect(self.showNormal)
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self._force_quit)

        tray_menu.addAction(restore_action)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

        self._is_force_quit = False

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.nav_buttons = []
        self._setup_global_header()
        self._setup_ui()

        self._initialize_context()

    def _force_quit(self):
        self._is_force_quit = True
        self.close()

    def closeEvent(self, event):
        if not self._is_force_quit:
            event.ignore()
            self.hide()
            self.tray_icon.showMessage(
                "Workout Active",
                "App minimized to tray. Your rest timers are still running.",
                QSystemTrayIcon.MessageIcon.Information,
                2000
            )
        else:
            super().closeEvent(event)

    def _setup_global_header(self):
        self.header_widget = QWidget()
        self.header_widget.setStyleSheet("background-color: #2c2c2c; border-bottom: 1px solid #3d3d3d;")
        header_layout = QHBoxLayout(self.header_widget)
        header_layout.setContentsMargins(15, 10, 15, 10)

        switcher_layout = QHBoxLayout()
        switcher_layout.setSpacing(10)

        lbl_user = QLabel("👤 User:")
        lbl_user.setStyleSheet("color: #b0b0b0; font-weight: bold;")

        self.user_combo = QComboBox()
        self.user_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.user_combo.setStyleSheet("padding: 5px; border-radius: 4px; background: #1e1e1e; color: white;")
        self.user_combo.currentIndexChanged.connect(self._on_user_changed)

        btn_add_user = QPushButton("")
        btn_add_user.setIcon(qta.icon('fa5s.user-plus', color='white'))
        btn_add_user.setFixedSize(25, 25)
        btn_add_user.setStyleSheet("background-color: #4CAF50; border-radius: 4px;")
        btn_add_user.clicked.connect(self._add_new_user)

        btn_del_user = QPushButton("")
        btn_del_user.setIcon(qta.icon('fa5s.user-minus', color='white'))
        btn_del_user.setFixedSize(25, 25)
        btn_del_user.setStyleSheet("background-color: #F44336; border-radius: 4px;")
        btn_del_user.clicked.connect(self._delete_current_user)

        lbl_program = QLabel("📋 Program:")
        lbl_program.setStyleSheet("color: #b0b0b0; font-weight: bold;")

        self.program_combo = QComboBox()
        self.program_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.program_combo.setStyleSheet("padding: 5px; border-radius: 4px; background: #1e1e1e; color: white;")
        self.program_combo.currentIndexChanged.connect(self._on_program_changed)

        btn_add_program = QPushButton("") # Not directly connected right now, serves as an anchor for sandbox
        btn_add_program.setIcon(qta.icon('fa5s.folder-plus', color='white'))
        btn_add_program.setFixedSize(25, 25)
        btn_add_program.setStyleSheet("background-color: #2196F3; border-radius: 4px;")
        btn_add_program.setToolTip("Go to Program Sandbox to add new programs.")

        btn_del_program = QPushButton("")
        btn_del_program.setIcon(qta.icon('fa5s.trash-alt', color='white'))
        btn_del_program.setFixedSize(25, 25)
        btn_del_program.setStyleSheet("background-color: #F44336; border-radius: 4px;")
        btn_del_program.clicked.connect(self._delete_current_program)

        switcher_layout.addWidget(lbl_user)
        switcher_layout.addWidget(self.user_combo)
        switcher_layout.addWidget(btn_add_user)
        switcher_layout.addWidget(btn_del_user)
        switcher_layout.addSpacing(15)
        switcher_layout.addWidget(lbl_program)
        switcher_layout.addWidget(self.program_combo)
        switcher_layout.addWidget(btn_add_program)
        switcher_layout.addWidget(btn_del_program)

        header_layout.addLayout(switcher_layout)
        header_layout.addStretch()

        self.lbl_global_timer = QLabel("No Active Session")
        self.lbl_global_timer.setStyleSheet("font-size: 14px; font-weight: bold; color: #b0b0b0;")
        header_layout.addWidget(self.lbl_global_timer)

    def _initialize_context(self):
        self.user_combo.blockSignals(True)
        self.user_combo.clear()
        users = WorkoutDatabaseManager.get_all_users()
        for u in users:
            self.user_combo.addItem(u['username'], u['id'])
        self.user_combo.blockSignals(False)

        if self.user_combo.count() > 0:
            self._on_user_changed(0)

    def _on_user_changed(self, index):
        user_id = self.user_combo.itemData(index)
        if not user_id: return

        event_bus.USER_CHANGED.emit(user_id)

        self.program_combo.blockSignals(True)
        self.program_combo.clear()

        programs = WorkoutDatabaseManager.get_programs_for_user(user_id)
        active_idx = 0
        for i, p in enumerate(programs):
            self.program_combo.addItem(p['name'], p['id'])
            if p['is_active']:
                active_idx = i

        if programs:
            self.program_combo.setCurrentIndex(active_idx)
        self.program_combo.blockSignals(False)

        if self.program_combo.count() > 0:
            self._on_program_changed(self.program_combo.currentIndex())

    def _add_new_user(self):
        username, ok = QInputDialog.getText(self, "New User", "Enter new username:")
        if ok and username.strip():
            try:
                new_id = WorkoutDatabaseManager.create_user(username.strip())
                self._initialize_context()
                index = self.user_combo.findData(new_id)
                if index >= 0:
                    self.user_combo.setCurrentIndex(index)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not create user: {e}")

    def _on_program_changed(self, index):
        user_id = self.user_combo.currentData()
        program_id = self.program_combo.itemData(index)
        if not program_id or not user_id: return
        WorkoutDatabaseManager.set_active_program(user_id, program_id)
        event_bus.PROGRAM_CHANGED.emit(program_id)

    def _setup_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        master_layout = QVBoxLayout(main_widget)
        master_layout.setContentsMargins(0, 0, 0, 0)
        master_layout.setSpacing(0)
        master_layout.addWidget(self.header_widget)

        body_widget = QWidget()
        body_layout = QHBoxLayout(body_widget)
        body_layout.setContentsMargins(0, 0, 0, 0)
        master_layout.addWidget(body_widget)

        self._setup_sidebar()
        body_layout.addWidget(self.sidebar)

        self._setup_stacked_views()
        body_layout.addWidget(self.stacked_widget)

    def _setup_sidebar(self):
        self.sidebar = QWidget()
        self.sidebar.setFixedWidth(200)
        self.sidebar.setStyleSheet("background-color: palette(alternate-base);")

        self.sidebar_layout = QVBoxLayout(self.sidebar)
        self.sidebar_layout.setContentsMargins(10, 20, 10, 20)
        self.sidebar_layout.setSpacing(10)

        logo = QLabel("HYBRID\nTRACKER")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setStyleSheet("font-size: 20px; font-weight: 900; margin-bottom: 20px;")
        self.sidebar_layout.addWidget(logo)

        self.sidebar_layout.addStretch()

    def _setup_stacked_views(self):
        self._next_idx = 0
        self._stacked_widget_list = []
        self.stacked_widget = FadingStackedWidget()

        self.dashboard_view = DashboardView()
        self._add_stacked_widget(self.dashboard_view, "Dashboard", qta.icon('fa5s.chart-line', color='white'))

        self.workout_view = QWidget()
        workout_layout = QHBoxLayout(self.workout_view)
        self.minimap = WorkoutMinimap()
        self.session_controller = WorkoutSessionController()
        self.active_tracker = ActiveTrackerWidget(
            controller=self.session_controller,
            minimap=self.minimap,
            global_timer_lbl=self.lbl_global_timer,
        )
        self.workout_container = WorkoutContainer(self.minimap, self.active_tracker)
        self._add_stacked_widget(self.workout_container, "Active Workout")

        self.program_sandbox_view = ProgramSandboxView()
        self._add_stacked_widget(self.program_sandbox_view, "Program Sandbox")

        self.history_view = WorkoutHistoryView()
        self._add_stacked_widget(self.history_view, "Workout History")

        self.bodyweight_view = BodyweightHubView()
        self._add_stacked_widget(self.bodyweight_view, "Bodyweight Hub")

        self.exercise_dict_view = ExerciseDictionaryView()
        self._add_stacked_widget(self.exercise_dict_view, "Exercise Bank")

        self.equipment_view = EquipmentView()
        self._add_stacked_widget(self.equipment_view, "My Garage")

        self.settings_view = SettingsView()
        self._add_stacked_widget(self.settings_view, "Settings")

        self.clinical_view = ClinicalAnalyticsView()
        self._add_stacked_widget(self.clinical_view, "Clinical Analytics", qta.icon('fa5s.heartbeat', color='#FF9800'))

        self._switch_view(0)

    def _add_stacked_widget(self, widget_view, btn_name: str, icon=None):
        self._stacked_widget_list.append(widget_view)
        self.stacked_widget.addWidget(widget_view)

        this_button = create_sidebar_button(btn_name)
        if icon: this_button.setIcon(icon)
        this_button.clicked.connect(lambda *args, index=self._next_idx: self._switch_view(index))
        self.nav_buttons.append(this_button)

        add_button_above_stretch(self.sidebar_layout, this_button)
        self._next_idx += 1

    def _switch_view(self, index: int):
        self.stacked_widget.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;" if i == index else "")

        for i, view in enumerate(self._stacked_widget_list):
            if hasattr(view, 'set_active_view'):
                view.set_active_view(i == index)

    def _delete_current_user(self):
        user_id = self.user_combo.currentData()
        if user_id:
            reply = QMessageBox.question(self, "Delete User", "Are you sure you want to delete this user and all their history?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                WorkoutDatabaseManager.delete_user(user_id)
                self._initialize_context()

    def _delete_current_program(self):
        prog_id = self.program_combo.currentData()
        if prog_id:
            reply = QMessageBox.question(self, "Delete Program", "Are you sure you want to delete this program?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                WorkoutDatabaseManager.delete_program(prog_id)
                self._on_user_changed(self.user_combo.currentIndex())