# ui/main_window.py
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
    QPushButton, QStackedWidget, QLabel, QSystemTrayIcon, QMenu,
    QComboBox, QInputDialog, QMessageBox
)
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtCore import Qt

from core.events import event_bus
from modules.workout.session import WorkoutSessionController
from ui.components.active_tracker import ActiveTrackerWidget
from ui.components.minimap import WorkoutMinimap
from ui.views.base_view import BaseView
from ui.views.bodyweight_hub import BodyweightHubView
from ui.views.dashboard import DashboardView
from ui.views.history import WorkoutHistoryView
from ui.views.program_sandbox import ProgramSandboxView
from ui.views.routine_builder import RoutineBuilderView
from ui.views.settings import SettingsView
from utils.gui_utils import add_button_above_stretch, create_sidebar_button

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
        self.resize(1100, 750)

        # Minimize to System Tray
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
        
        # Main widget
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
        """Intercept the X button to minimize to tray instead."""
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

        # --- User & Program Context Switchers ---
        switcher_layout = QHBoxLayout()
        switcher_layout.setSpacing(10)
        
        lbl_user = QLabel("👤 User:")
        lbl_user.setStyleSheet("color: #b0b0b0; font-weight: bold;")
        self.user_combo = QComboBox()
        self.user_combo.setStyleSheet("padding: 5px; border-radius: 4px; background: #1e1e1e; color: white;")
        self.user_combo.currentIndexChanged.connect(self._on_user_changed)
        
        # New user button
        btn_add_user = QPushButton("+")
        btn_add_user.setFixedSize(25, 25)
        btn_add_user.setStyleSheet("background-color: #4CAF50; color: white; border-radius: 4px; font-weight: bold;")
        btn_add_user.clicked.connect(self._add_new_user)

        lbl_program = QLabel("📋 Program:")
        lbl_program.setStyleSheet("color: #b0b0b0; font-weight: bold;")
        self.program_combo = QComboBox()
        self.program_combo.setStyleSheet("padding: 5px; border-radius: 4px; background: #1e1e1e; color: white;")
        self.program_combo.currentIndexChanged.connect(self._on_program_changed)
        
        switcher_layout.addWidget(lbl_user)
        switcher_layout.addWidget(self.user_combo)
        switcher_layout.addWidget(btn_add_user)
        switcher_layout.addWidget(lbl_program)
        switcher_layout.addWidget(self.program_combo)
        
        header_layout.addLayout(switcher_layout)
        header_layout.addStretch()

        self.lbl_global_timer = QLabel("No Active Session")
        self.lbl_global_timer.setStyleSheet("font-size: 14px; font-weight: bold; color: #b0b0b0;")
        header_layout.addWidget(self.lbl_global_timer)

    def _initialize_context(self):
        """Loads users and their programs into the header dropdowns."""
        self.user_combo.blockSignals(True)
        self.user_combo.clear()
        
        from core.db_operations import WorkoutDatabaseManager
        users = WorkoutDatabaseManager.get_all_users()
        
        for u in users:
            self.user_combo.addItem(u['username'], u['id'])
            
        self.user_combo.blockSignals(False)
        
        if self.user_combo.count() > 0:
            self._on_user_changed(0) 
            
    def _on_user_changed(self, index):
        user_id = self.user_combo.itemData(index)
        if not user_id: return
        
        # CORRECT PyQt6 Event emission
        event_bus.USER_CHANGED.emit(user_id)
        
        self.program_combo.blockSignals(True)
        self.program_combo.clear()
        
        from core.db_operations import WorkoutDatabaseManager
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
                self._initialize_context() # Reload dropdowns
                index = self.user_combo.findData(new_id)
                if index >= 0:
                    self.user_combo.setCurrentIndex(index)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not create user: {e}")

    def _on_program_changed(self, index):
        user_id = self.user_combo.currentData()
        program_id = self.program_combo.itemData(index)
        if not program_id or not user_id: return
        
        from core.db_operations import WorkoutDatabaseManager
        WorkoutDatabaseManager.set_active_program(user_id, program_id)
        
        # CORRECT PyQt6 Event emission
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
        self.stacked_widget = QStackedWidget()
        
        # 1. Dashboard
        self.dashboard_view = DashboardView()
        self._add_stacked_widget(self.dashboard_view, "Dashboard")
        
        # 2. Active Workout
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

        # 3. Unified Program Sandbox (Replaces Routine & Program Builders)
        self.program_sandbox_view = ProgramSandboxView()
        self._add_stacked_widget(self.program_sandbox_view, "Program Sandbox")
        
        # 4. Workout History
        self.history_view = WorkoutHistoryView()
        self._add_stacked_widget(self.history_view, "Workout History")
        
        # 5. Bodyweight Hub
        self.bodyweight_view = BodyweightHubView()
        self._add_stacked_widget(self.bodyweight_view, "Bodyweight Hub")
        
        # 6. Settings
        self.settings_view = SettingsView()
        self._add_stacked_widget(self.settings_view, "Settings")
        
        self._switch_view(0) # Initialize default view

    def _add_stacked_widget(self, widget_view, btn_name: str):
        # Add to widgets
        self._stacked_widget_list.append(widget_view)
        self.stacked_widget.addWidget(widget_view)

        # Add and connect button
        this_button = create_sidebar_button(btn_name)
        this_button.clicked.connect(lambda *args, index=self._next_idx: self._switch_view(index))
        self.nav_buttons.append(this_button)

        # Add the button above the stretch
        add_button_above_stretch(self.sidebar_layout, this_button)

        self._next_idx += 1

    def _switch_view(self, index: int):
        self.stacked_widget.setCurrentIndex(index)
        
        for i, btn in enumerate(self.nav_buttons):
            btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;" if i == index else "")
                
        # Trigger Lazy Load
        for i, view in enumerate(self._stacked_widget_list):
            if hasattr(view, 'set_active_view'):
                view.set_active_view(i == index)