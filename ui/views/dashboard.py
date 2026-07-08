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
from ui.views.base_view import BaseView
from core.events import event_bus

class DashboardView(BaseView):
    def __init__(self, parent=None):
        super().__init__(parent)
        event_bus.WORKOUT_COMPLETED.connect(self.refresh_data) # Live redraw after review dialog
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)

        # --- TOP SECTION: Title, Calendar, Heatmap ---
        top_layout = QHBoxLayout()
        
        left_top_layout = QVBoxLayout()
        title = QLabel("Performance Dashboard")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        left_top_layout.addWidget(title)
        
        self.calendar = QCalendarWidget()
        self.calendar.setFixedSize(350, 200)
        self.calendar.setStyleSheet("background-color: #2d2d2d; color: white;")
        left_top_layout.addWidget(self.calendar)
        top_layout.addLayout(left_top_layout)

        self.heatmap = AnatomicalHeatmap()
        top_layout.addWidget(self.heatmap, stretch=1)
        
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
        self.fig = Figure(figsize=(8, 4), dpi=100)
        self.fig.patch.set_facecolor('#1e1e1e')
        self.canvas = FigureCanvas(self.fig)
        self.layout.addWidget(self.canvas)
        self.ax = self.fig.add_subplot(111)

    def refresh_data(self):
        self._highlight_calendar_dates()
        volume_map = WorkoutDatabaseManager.get_active_program_volume(self.current_user_id)
        self.heatmap.update_heatmap(volume_map)
        
        exercises = WorkoutDatabaseManager.get_tracked_exercises(self.current_user_id)
        self.exercise_dropdown.blockSignals(True)
        self.exercise_dropdown.clear()
        
        self.exercise_dropdown.addItem("Overview: Weight Loss vs. Calisthenics Strength")
        self.exercise_dropdown.addItems(exercises)
        self.exercise_dropdown.blockSignals(False)
        self._plot_trend_data(self.exercise_dropdown.currentText())

    def _highlight_calendar_dates(self):
        dates = WorkoutDatabaseManager.get_all_workout_dates(self.current_user_id)
        fmt = QTextCharFormat()
        fmt.setBackground(QColor("#4CAF50"))
        fmt.setForeground(QColor("white"))
        fmt.setFontWeight(75)

        self.calendar.setDateTextFormat(QDate(), QTextCharFormat()) 
        for date_str in dates:
            y, m, d = map(int, date_str.split('-'))
            qdate = QDate(y, m, d)
            self.calendar.setDateTextFormat(qdate, fmt)

    def _plot_trend_data(self, selection: str):
        self.fig.clear()
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor('#1e1e1e')
        self.fig.patch.set_facecolor('#1e1e1e')
        
        if selection == "Overview: Weight Loss vs. Calisthenics Strength":
            self._plot_bw_vs_calisthenics()
        else:
            self._plot_1rm_standard(selection) 

    def _plot_bw_vs_calisthenics(self):
        import numpy as np
        bw_data = WorkoutDatabaseManager.get_bodyweight_history(self.current_user_id) 
        cal_data = WorkoutDatabaseManager.get_calisthenics_volume_trend(self.current_user_id) 

        if not bw_data and not cal_data:
            self.canvas.draw(); return
            
        all_dates = sorted(list(set([d['date'] for d in bw_data] + list(cal_data.keys()))))
        x_numeric = np.arange(len(all_dates))
        
        bw_y = []
        last_bw = bw_data[0]['weight_lbs'] if bw_data else 180
        bw_dict = {d['date']: d['weight_lbs'] for d in bw_data}
        for d in all_dates:
            last_bw = bw_dict.get(d, last_bw)
            bw_y.append(last_bw)

        cal_y = [cal_data.get(d, 0) for d in all_dates]

        self.ax.plot(x_numeric, bw_y, color='#FF9800', marker='o', label='Bodyweight', linewidth=2)
        self.ax.set_ylabel("Morning Bodyweight (lbs)", color='#FF9800')
        self.ax.tick_params(axis='y', labelcolor='#FF9800')
        self.ax.tick_params(axis='x', colors='white')
        
        ax2 = self.ax.twinx()
        ax2.bar(x_numeric, cal_y, color='#2196F3', alpha=0.5, label='Calisthenics Tonnage')
        ax2.set_ylabel("Total Tonnage (lbs)", color='#2196F3')
        ax2.tick_params(axis='y', labelcolor='#2196F3')
        
        self.ax.set_title("Mathematical Proof: Weight Loss Driving Relative Strength", color='white', pad=15)
        self.ax.set_xticks(x_numeric)
        self.ax.set_xticklabels(all_dates, rotation=45)
        self.fig.tight_layout()
        self.canvas.draw()

    def _plot_1rm_standard(self, exercise_name: str):
        if not exercise_name: return
        
        self.ax.clear()
        self.ax.set_facecolor('#1e1e1e')
        
        self.ax.tick_params(axis='both', colors='white', labelcolor='white')
        self.ax.xaxis.label.set_color('white')
        self.ax.yaxis.label.set_color('white')
        for spine in self.ax.spines.values(): spine.set_edgecolor('#555555')

        data = WorkoutDatabaseManager.get_1rm_trends(self.current_user_id, exercise_name)
        if not data:
            self.canvas.draw()
            return

        dates = list(data.keys())
        weights = list(data.values())
        x_numeric = np.arange(len(dates))
        
        self.ax.plot(x_numeric, weights, marker='o', color='#2196F3', label='Actual 1RM', linewidth=2, markersize=8)

        if len(weights) > 1:
            m, b = np.polyfit(x_numeric, weights, 1)
            x_future = np.arange(len(dates) + 2)
            y_pred = m * x_future + b
            self.ax.plot(x_future, y_pred, linestyle='--', color='#FF9800', label='Predicted Trend')

        self.ax.set_title(f"Strength Progression: {exercise_name}", color='white', pad=15)
        self.ax.set_ylabel("Estimated 1RM (lbs)", color='white')
        self.ax.set_xticks(x_numeric)
        self.ax.set_xticklabels(dates, rotation=45, color='white')
        
        legend = self.ax.legend(facecolor='#2d2d2d', edgecolor='#555555')
        for text in legend.get_texts(): text.set_color("white")

        self.fig.tight_layout()
        self.canvas.draw()