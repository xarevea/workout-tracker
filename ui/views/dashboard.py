from datetime import datetime

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QCalendarWidget, QMessageBox
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QTextCharFormat, QColor

import matplotlib
matplotlib.use('QtAgg')
import matplotlib.dates as mdates
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
        event_bus.WORKOUT_COMPLETED.connect(self.refresh_data) 
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
        
        self.calendar.clicked.connect(self._show_workout_summary)
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

    def _show_workout_summary(self, qdate):
        date_str = qdate.toString("yyyy-MM-dd")
        workouts = WorkoutDatabaseManager.get_workout_history(self.current_user_id)
        
        day_workouts = [w for w in workouts if w['date'].startswith(date_str)]

        if not day_workouts:
            QMessageBox.information(self, "No Workout", f"No workouts recorded on {date_str}.")
            return

        msg = f"Workouts on {date_str}:\n\n"
        for w in day_workouts:
            msg += f"• {w['name']} ({w['duration_minutes']} min)\n"
            logs = WorkoutDatabaseManager.get_workout_logs(w['id'])
            for log in logs:
                msg += f"   - {log['exercise']}: {log['reps']} reps @ {log['weight_lbs']} lbs\n"
            msg += "\n"

        QMessageBox.information(self, f"Workout Details: {date_str}", msg)
    
    def _plot_bw_vs_calisthenics(self):
        bw_data = WorkoutDatabaseManager.get_bodyweight_history(self.current_user_id) 
        cal_data = WorkoutDatabaseManager.get_calisthenics_volume_trend(self.current_user_id) 

        if not bw_data and not cal_data:
            self.canvas.draw(); return
            
        all_dates = sorted(list(set([d['date'] for d in bw_data] + list(cal_data.keys()))))
        date_objs = [datetime.strptime(d, "%Y-%m-%d") for d in all_dates]
        mdates_vals = mdates.date2num(date_objs)
        
        bw_y = []
        last_bw = bw_data[0]['weight_lbs'] if bw_data else 180
        bw_dict = {d['date']: d['weight_lbs'] for d in bw_data}
        for d in all_dates:
            last_bw = bw_dict.get(d, last_bw)
            bw_y.append(last_bw)

        cal_y = [cal_data.get(d, 0) for d in all_dates]

        self.ax.plot(date_objs, bw_y, color='#FF9800', marker='o', label='Bodyweight', linewidth=2)
        self.ax.set_ylabel("Morning Bodyweight (lbs)", color='#FF9800')
        self.ax.tick_params(axis='y', labelcolor='#FF9800')
        self.ax.tick_params(axis='x', colors='white')
        
        ax2 = self.ax.twinx()
        ax2.bar(mdates_vals, cal_y, width=0.6, color='#2196F3', alpha=0.5, label='Calisthenics Tonnage')
        ax2.set_ylabel("Total Tonnage (lbs)", color='#2196F3')
        ax2.tick_params(axis='y', labelcolor='#2196F3')
        
        self.ax.set_title("Mathematical Proof: Weight Loss Driving Relative Strength", color='white', pad=15)
        
        self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d, %Y'))
        self.ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        self.fig.autofmt_xdate(rotation=45)
        self.fig.tight_layout()
        self.canvas.draw()

    def _plot_1rm_standard(self, exercise_name: str):
        if not exercise_name: return
        self.ax.clear()
        self.ax.set_facecolor('#1e1e1e')
        self.ax.tick_params(axis='both', colors='white', labelcolor='white')
        self.ax.xaxis.label.set_color('white'); self.ax.yaxis.label.set_color('white')
        for spine in self.ax.spines.values(): spine.set_edgecolor('#555555')

        data = WorkoutDatabaseManager.get_1rm_trends(self.current_user_id, exercise_name)
        if not data: self.canvas.draw(); return

        dates = list(data.keys())
        weights = list(data.values())
        date_objs = [datetime.strptime(d, "%Y-%m-%d") for d in dates]
        mdates_vals = mdates.date2num(date_objs)
        
        self.ax.plot(date_objs, weights, marker='o', color='#2196F3', label='Actual 1RM', linewidth=2, markersize=8)

        if len(weights) > 1:
            m, b = np.polyfit(mdates_vals, weights, 1)
            future_dates = np.linspace(mdates_vals[0], mdates_vals[-1] + 14, len(dates) + 2)
            y_pred = m * future_dates + b
            future_objs = mdates.num2date(future_dates)
            self.ax.plot(future_objs, y_pred, linestyle='--', color='#FF9800', label='Predicted Trend')

        self.ax.set_title(f"Strength Progression: {exercise_name}", color='white', pad=15)
        self.ax.set_ylabel("Estimated 1RM (lbs)", color='white')
        
        self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d, %Y'))
        self.ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        self.fig.autofmt_xdate(rotation=45)
        
        legend = self.ax.legend(facecolor='#2d2d2d', edgecolor='#555555')
        for text in legend.get_texts(): text.set_color("white")

        self.fig.tight_layout()
        self.canvas.draw()