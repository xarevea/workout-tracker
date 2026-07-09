from datetime import datetime

import pyqtgraph as pg
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QCalendarWidget, QMessageBox
from PyQt6.QtCore import Qt, QDate, QThreadPool
from PyQt6.QtGui import QTextCharFormat, QColor

import matplotlib
matplotlib.use('QtAgg')
import matplotlib.dates as mdates
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np

from core.db_operations import WorkoutDatabaseManager
from core.events import event_bus
from ui.components.body_heatmap import AnatomicalHeatmap
from ui.views.base_view import BaseView
from utils.threads import Worker

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
        control_layout.addWidget(QLabel("Select Analysis Metric:"))
        self.exercise_dropdown = QComboBox()
        self.exercise_dropdown.currentTextChanged.connect(self._plot_trend_data)
        control_layout.addWidget(self.exercise_dropdown)
        control_layout.addStretch()
        self.layout.addLayout(control_layout)

        # --- BOTTOM SECTION: PyQtGraph Canvas ---
        self.graph_widget = pg.PlotWidget()
        self.layout.addWidget(self.graph_widget)

    def refresh_data(self):
        self._highlight_calendar_dates()
        volume_map = WorkoutDatabaseManager.get_active_program_volume(self.current_user_id)
        self.heatmap.update_heatmap(volume_map)
        
        exercises = WorkoutDatabaseManager.get_tracked_exercises(self.current_user_id)
        self.exercise_dropdown.blockSignals(True)
        self.exercise_dropdown.clear()
        
        self.exercise_dropdown.addItem("Overview: Total Weekly Volume (Tonnage)")
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
        if not selection: return
        
        # 1. Safely wipe the existing graph entirely to prevent Dual-Axis ghosting
        self.layout.removeWidget(self.graph_widget)
        self.graph_widget.deleteLater()
        
        self.graph_widget = pg.PlotWidget()
        self.graph_widget.setBackground('#1e1e1e')
        self.layout.addWidget(self.graph_widget)
        
        # 2. Add loading text directly to the ViewBox
        text = pg.TextItem("Crunching Dataset...", color='white', anchor=(0.5, 0.5))
        self.graph_widget.addItem(text)
        
        # 3. Dispatch the appropriate thread
        if selection == "Overview: Weight Loss vs. Calisthenics Strength":
            worker = Worker(self._fetch_bw_vs_cal_data)
            worker.signals.result.connect(self._render_bw_vs_cal)
        elif selection == "Overview: Total Weekly Volume (Tonnage)":
            worker = Worker(self._fetch_tonnage_data)
            worker.signals.result.connect(self._render_tonnage)
        else:
            worker = Worker(self._fetch_1rm_data, selection)
            worker.signals.result.connect(lambda res: self._render_1rm_data(selection, res))
            
        QThreadPool.globalInstance().start(worker)

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

    def _fetch_bw_vs_cal_data(self):
        """Runs in the background thread."""
        bw = WorkoutDatabaseManager.get_bodyweight_history(self.current_user_id) 
        cal = WorkoutDatabaseManager.get_calisthenics_volume_trend(self.current_user_id) 
        return bw, cal

    def _render_bw_vs_cal(self, data):
        self.graph_widget.clear() # Clear loading text
        bw_data, cal_data = data
        if not bw_data and not cal_data: return
            
        # Extract and sort unique dates
        all_dates = sorted(list(set([d['date'] for d in bw_data] + list(cal_data.keys()))))
        timestamps = [datetime.strptime(d, "%Y-%m-%d").timestamp() for d in all_dates]
        
        bw_y = []
        last_bw = bw_data[0]['weight_lbs'] if bw_data else 180
        bw_dict = {d['date']: d['weight_lbs'] for d in bw_data}
        for d in all_dates:
            last_bw = bw_dict.get(d, last_bw)
            bw_y.append(last_bw)

        cal_y = [cal_data.get(d, 0) for d in all_dates]

        # 1. Setup the X-Axis as Dates
        date_axis = pg.DateAxisItem(orientation='bottom')
        self.graph_widget.setAxisItems({'bottom': date_axis})
        
        # 2. Setup the PlotItem (Base Layer for Bodyweight)
        p1 = self.graph_widget.plotItem
        p1.setLabels(left='Bodyweight (lbs)', bottom='Date')
        p1.getAxis('left').setTextPen('#FF9800')
        
        # Plot Bodyweight
        pen = pg.mkPen(color='#FF9800', width=2)
        p1.plot(timestamps, bw_y, pen=pen, symbol='o', symbolSize=6, symbolBrush='#FF9800')

        # 3. Setup the Dual Y-Axis (Tonnage)
        p2 = pg.ViewBox()
        p1.showAxis('right')
        p1.scene().addItem(p2)
        p1.getAxis('right').linkToView(p2)
        p2.setXLink(p1)
        p1.getAxis('right').setLabel('Calisthenics Tonnage (lbs)')
        p1.getAxis('right').setTextPen('#2196F3')

        # Link view resizing
        def updateViews():
            p2.setGeometry(p1.vb.sceneBoundingRect())
            p2.linkedViewChanged(p1.vb, p2.XAxis)
            
        updateViews()
        p1.vb.sigResized.connect(updateViews)

        # Plot Tonnage Bar Graph on P2
        # Need to calculate width (in seconds) for bars. (86400 = 1 day)
        bar_graph = pg.BarGraphItem(x=timestamps, height=cal_y, width=86400 * 0.8, brush='#2196F388') # 88 is alpha transparency
        p2.addItem(bar_graph)

        self.graph_widget.setTitle("Weight Loss Driving Relative Strength", color="white", size="14pt")

    def _fetch_1rm_data(self, exercise_name: str):
        return WorkoutDatabaseManager.get_1rm_trends(self.current_user_id, exercise_name)

    def _render_1rm_data(self, exercise_name: str, data: dict):
        self.graph_widget.clear()

        if not data: return

        dates = list(data.keys())
        weights = list(data.values())
        
        # PyQtGraph requires unix timestamps for its DateAxis
        timestamps = [datetime.strptime(d, "%Y-%m-%d").timestamp() for d in dates]
        
        # 1. Plot the actual points and lines
        pen = pg.mkPen(color='#2196F3', width=3)
        self.graph_widget.plot(timestamps, weights, pen=pen, symbol='o', symbolSize=8, symbolBrush='#2196F3', name="Estimated 1RM")

        # 2. Add Trendline if enough data
        if len(weights) > 1:
            import numpy as np
            m, b = np.polyfit(timestamps, weights, 1)
            future_timestamps = np.linspace(timestamps[0], timestamps[-1] + (86400 * 14), len(dates) + 2)
            y_pred = m * future_timestamps + b
            
            trend_pen = pg.mkPen(color='#FF9800', width=2, style=Qt.PenStyle.DashLine)
            self.graph_widget.plot(future_timestamps, y_pred, pen=trend_pen, name="Predicted Trend")

        self.graph_widget.setTitle(f"Strength Progression: {exercise_name}", color="white", size="14pt")
        self.graph_widget.setLabel('left', "Estimated 1RM (lbs)", color="white")
        
        # Add interactive legend
        self.graph_widget.addLegend()

    def _fetch_tonnage_data(self):
        return WorkoutDatabaseManager.get_weekly_tonnage(self.current_user_id)

    def _render_tonnage(self, data: dict):
        self.graph_widget.clear()
        
        # Change axis back to normal for Bar Chart
        self.graph_widget.setAxisItems({'bottom': pg.AxisItem(orientation='bottom')})

        if not data: return
            
        weeks = [int(w) for w in data.keys()]
        tonnages = list(data.values())
        
        # PyQtGraph BarGraphItem
        bg = pg.BarGraphItem(x=weeks, height=tonnages, width=0.6, brush='#4CAF50')
        self.graph_widget.addItem(bg)
        
        self.graph_widget.setTitle("Total Weekly Volume (Tonnage)", color="white", size="14pt")
        self.graph_widget.setLabel('left', "Total Lbs Lifted", color="white")
        self.graph_widget.setLabel('bottom', "Week Number of the Year", color="white")