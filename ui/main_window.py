# ui/main_window.py
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
    QPushButton, QStackedWidget, QLabel
)
from PyQt6.QtCore import Qt

from ui.components.minimap import WorkoutMinimap
from ui.components.active_tracker import ActiveTrackerWidget
from modules.workout.session import WorkoutSessionController

from ui.views.dashboard import DashboardView
from ui.views.routine_builder import RoutineBuilderView
from ui.views.settings import SettingsView

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hybrid Tracker")
        self.resize(1100, 750)
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self._setup_sidebar()
        self._setup_stacked_views()

    def _setup_sidebar(self):
        self.sidebar = QWidget()
        self.sidebar.setFixedWidth(200)
        self.sidebar.setStyleSheet("background-color: palette(alternate-base);")
        
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(10, 20, 10, 20)
        sidebar_layout.setSpacing(10)

        logo = QLabel("HYBRID\nTRACKER")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setStyleSheet("font-size: 20px; font-weight: 900; margin-bottom: 20px;")
        sidebar_layout.addWidget(logo)

        self.btn_dashboard = QPushButton("Dashboard")
        self.btn_workout = QPushButton("Active Workout")
        self.btn_routine = QPushButton("Routine Builder")
        self.btn_settings = QPushButton("Settings")
        
        self.nav_buttons = [self.btn_dashboard, self.btn_workout, self.btn_routine, self.btn_settings]
        
        for btn in self.nav_buttons:
            btn.setMinimumHeight(40)
            sidebar_layout.addWidget(btn)
            
        sidebar_layout.addStretch()
        self.main_layout.addWidget(self.sidebar)

    def _setup_stacked_views(self):
        self.stacked_widget = QStackedWidget()
        
        # 1. Dashboard
        self.dashboard_view = DashboardView()
        
        # 2. Active Workout
        self.workout_view = QWidget()
        workout_layout = QHBoxLayout(self.workout_view)
        
        self.minimap = WorkoutMinimap()
        self.session_controller = WorkoutSessionController()
        
        self.active_tracker = ActiveTrackerWidget(
            controller=self.session_controller, 
            minimap=self.minimap
        )
        
        workout_layout.addWidget(self.minimap, stretch=1)
        workout_layout.addWidget(self.active_tracker, stretch=3)

        # 3. Routine Builder
        self.routine_view = RoutineBuilderView()

        # 4. Settings
        self.settings_view = SettingsView()

        # Add to stack
        self.stacked_widget.addWidget(self.dashboard_view)
        self.stacked_widget.addWidget(self.workout_view)
        self.stacked_widget.addWidget(self.routine_view)
        self.stacked_widget.addWidget(self.settings_view)
        
        self.main_layout.addWidget(self.stacked_widget)

        # Connect Navigation
        self.btn_dashboard.clicked.connect(lambda: self._switch_view(0))
        self.btn_workout.clicked.connect(lambda: self._switch_view(1))
        self.btn_routine.clicked.connect(lambda: self._switch_view(2))
        self.btn_settings.clicked.connect(lambda: self._switch_view(3))
        
        self._switch_view(0) # Initialize default view

    def _switch_view(self, index: int):
        """Switches view, highlights nav, and forces a data refresh."""
        self.stacked_widget.setCurrentIndex(index)
        
        # Highlight active panel
        for i, btn in enumerate(self.nav_buttons):
            if i == index:
                btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
            else:
                btn.setStyleSheet("")
                
        # Force refresh data so dropdowns are never blank
        if index == 0:
            self.dashboard_view.refresh_data()
        elif index == 1:
            self.active_tracker.refresh_data()
        elif index == 2:
            self.routine_view.refresh_data()
        elif index == 3:
            self.settings_view.refresh_data()