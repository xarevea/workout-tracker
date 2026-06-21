# ui/views/dashboard.py
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QCalendarWidget
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QTextCharFormat, QColor

import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np

from core.db_operations import WorkoutDatabaseManager
from ui.components.body_heatmap import AnatomicalHeatmap

class DashboardView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)

        # --- TOP SECTION: Title & Calendar ---
        top_layout = QHBoxLayout()
        
        title_layout = QVBoxLayout()
        title = QLabel("Performance Dashboard")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        title_layout.addWidget(title)
        title_layout.addStretch()
        
        # Calendar View (Item 4)
        self.calendar = QCalendarWidget()
        self.calendar.setFixedSize(350, 200)
        self.calendar.setStyleSheet("background-color: #2d2d2d; color: white;")
        
        # Heatmap of muscle utilization
        self.heatmap = AnatomicalHeatmap()

        top_layout.addLayout(title_layout)
        top_layout.addWidget(self.calendar)
        top_layout.addWidget(self.heatmap)
        self.layout.addLayout(top_layout)

        # --- MIDDLE SECTION: Controls ---
        control_layout = QHBoxLayout()
        control_layout.addWidget(QLabel("Select Exercise to Analyze:"))
        
        self.exercise_dropdown = QComboBox()
        self.exercise_dropdown.currentTextChanged.connect(self._plot_trend_data)
        control_layout.addWidget(self.exercise_dropdown)
        control_layout.addStretch()
        self.layout.addLayout(control_layout)

        # --- BOTTOM SECTION: Matplotlib Canvas ---
        self.fig = Figure(figsize=(8, 5), dpi=100)
        self.fig.patch.set_facecolor('#1e1e1e')
        self.canvas = FigureCanvas(self.fig)
        self.layout.addWidget(self.canvas)
        
        self.ax = self.fig.add_subplot(111)

    def refresh_data(self):
        """Called by the main window to fetch fresh data."""
        self._highlight_calendar_dates()
        
        # Populate Dropdown
        exercises = WorkoutDatabaseManager.get_tracked_exercises()
        self.exercise_dropdown.blockSignals(True)
        self.exercise_dropdown.clear()
        self.exercise_dropdown.addItems(exercises)
        self.exercise_dropdown.blockSignals(False)

        # Update heatmap
        volume_map = WorkoutDatabaseManager.get_active_program_volume()
        self.heatmap.update_heatmap(volume_map)
        
        if exercises:
            self._plot_trend_data(exercises[0])

    def _highlight_calendar_dates(self):
        """Highlights days in the calendar where workouts occurred."""
        dates = WorkoutDatabaseManager.get_all_workout_dates()
        
        # Format for completed workouts (Green background)
        fmt = QTextCharFormat()
        fmt.setBackground(QColor("#4CAF50"))
        fmt.setForeground(QColor("white"))
        fmt.setFontWeight(75) # Bold

        # Clear existing formatting
        self.calendar.setDateTextFormat(QDate(), QTextCharFormat()) 
        
        for date_str in dates:
            y, m, d = map(int, date_str.split('-'))
            qdate = QDate(y, m, d)
            self.calendar.setDateTextFormat(qdate, fmt)

    def _plot_trend_data(self, exercise_name: str):
        """Plots Actual 1RM History + Predictive Trendline."""
        if not exercise_name: return
        
        self.ax.clear()
        self.ax.set_facecolor('#1e1e1e')
        self.ax.tick_params(colors='white')
        for spine in self.ax.spines.values(): spine.set_edgecolor('#555555')

        # Get actual data from DB
        data = WorkoutDatabaseManager.get_1rm_trends(exercise_name)
        if not data:
            self.canvas.draw()
            return

        dates = list(data.keys())
        weights = list(data.values())
        
        # Numeric X-axis for plotting and regression
        x_numeric = np.arange(len(dates))
        
        # 1. Plot Actual Recorded Data (Item 5b)
        self.ax.plot(x_numeric, weights, marker='o', color='#2196F3', label='Actual 1RM', linewidth=2, markersize=8)

        # 2. Calculate and Plot Predictive Linear Trend
        if len(weights) > 1:
            # Linear regression (y = mx + b)
            m, b = np.polyfit(x_numeric, weights, 1)
            
            # Predict out 2 sessions into the future
            x_future = np.arange(len(dates) + 2)
            y_pred = m * x_future + b
            
            # Plot the dashed prediction line
            self.ax.plot(x_future, y_pred, linestyle='--', color='#FF9800', label='Predicted Trend')

        # Formatting the chart
        self.ax.set_title(f"Strength Progression: {exercise_name}", color='white', pad=15)
        self.ax.set_ylabel("Estimated 1RM (lbs)", color='white')
        self.ax.set_xticks(x_numeric)
        self.ax.set_xticklabels(dates, rotation=45, color='white')
        
        legend = self.ax.legend(facecolor='#2d2d2d', edgecolor='#555555')
        for text in legend.get_texts(): text.set_color("white")

        # Make ticks more visible
        self.ax.tick_params(axis='both', colors='white', labelcolor='white')
        self.ax.xaxis.label.set_color('white')
        self.ax.yaxis.label.set_color('white')
        for spine in self.ax.spines.values(): 
            spine.set_edgecolor('#555555')

        self.fig.tight_layout()
        self.canvas.draw()