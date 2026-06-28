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
from ui.views.bodyweight_hub import BodyweightHubView
from ui.views.program_builder import ProgramBuilderView
from utils.gui_utils import add_button_above_stretch, create_sidebar_button

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

        self.nav_buttons = []
        self._setup_sidebar()
        self._setup_stacked_views()

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
        self.main_layout.addWidget(self.sidebar)

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
            minimap=self.minimap
        )
        
        workout_layout.addWidget(self.minimap, stretch=1)
        workout_layout.addWidget(self.active_tracker, stretch=3)
        self._add_stacked_widget(self.active_tracker, "Active Workout")

        # 3. Routine Builder
        self.routine_view = RoutineBuilderView()
        self._add_stacked_widget(self.routine_view, "Routine Builder")

        self.program_view = ProgramBuilderView()
        self._add_stacked_widget(self.program_view, "Program Builder")
        
        self.bodyweight_view = BodyweightHubView()
        self._add_stacked_widget(self.bodyweight_view, "Bodyweight Hub")
        
        # 4. Settings
        self.settings_view = SettingsView()
        self._add_stacked_widget(self.settings_view, "Settings")
        
        self.main_layout.addWidget(self.stacked_widget)
        
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
        """Switches view, highlights nav, and forces a data refresh."""
        self.stacked_widget.setCurrentIndex(index)
        
        # Highlight active panel
        for i, btn in enumerate(self.nav_buttons):
            if i == index:
                btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
            else:
                btn.setStyleSheet("")
                
        # Force refresh data so dropdowns are never blank
        self._stacked_widget_list[index].refresh_data()