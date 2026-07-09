# ========================================
# FILE PATH: ui/views/clinical_analytics.py
# ========================================
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTabWidget
from PyQt6.QtCore import QThreadPool
import pyqtgraph as pg
from datetime import datetime, timedelta

from core.db_operations import WorkoutDatabaseManager
from ui.views.base_view import BaseView
from utils.threads import Worker

class ClinicalAnalyticsView(BaseView):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        
        header = QLabel("Clinical & DPT Analytics")
        header.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(header)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self._setup_acwr_tab()
        self._setup_slings_tab()

    def refresh_data(self):
        # Dispatch background workers for both tabs
        worker_acwr = Worker(self._fetch_acwr_data)
        worker_acwr.signals.result.connect(self._render_acwr)
        QThreadPool.globalInstance().start(worker_acwr)

        worker_slings = Worker(self._fetch_sling_data)
        worker_slings.signals.result.connect(self._render_slings)
        QThreadPool.globalInstance().start(worker_slings)

    # ---------------------------------------------------------
    # TAB 1: ACUTE:CHRONIC WORKLOAD RATIO (ACWR)
    # ---------------------------------------------------------
    def _setup_acwr_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        info = QLabel(
            "<b>Acute:Chronic Workload Ratio (ACWR)</b><br>"
            "<span style='color: #4CAF50;'>Green Zone (0.8 - 1.3):</span> Optimal tissue adaptation.<br>"
            "<span style='color: #F44336;'>Red Zone (> 1.5):</span> Danger zone. 2x higher injury risk due to workload spiking."
        )
        layout.addWidget(info)
        
        self.graph_acwr = pg.PlotWidget()
        self.graph_acwr.setBackground('#1e1e1e')
        self.graph_acwr.setAxisItems({'bottom': pg.DateAxisItem(orientation='bottom')})
        self.graph_acwr.showGrid(x=True, y=True, alpha=0.3)
        
        # Add the clinical threshold regions
        sweet_spot = pg.LinearRegionItem(values=[0.8, 1.3], orientation=pg.LinearRegionItem.Horizontal, movable=False)
        sweet_spot.setBrush(pg.mkBrush(76, 175, 80, 40)) # Transparent Green
        self.graph_acwr.addItem(sweet_spot)
        
        danger_zone = pg.LinearRegionItem(values=[1.5, 3.0], orientation=pg.LinearRegionItem.Horizontal, movable=False)
        danger_zone.setBrush(pg.mkBrush(244, 67, 54, 40)) # Transparent Red
        self.graph_acwr.addItem(danger_zone)

        layout.addWidget(self.graph_acwr)
        self.tabs.addTab(tab, "ACWR Injury Predictor")

    def _fetch_acwr_data(self):
        daily_tonnage = WorkoutDatabaseManager.get_daily_tonnage(self.current_user_id)
        
        # Calculate for the last 60 days
        today = datetime.now()
        dates = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(60 + 28)] # need extra 28 days for chronic history
        dates.reverse()

        acwr_dates = []
        acwr_values = []

        # Iterate through the last 60 days
        for i in range(28, len(dates)):
            target_date = dates[i]
            
            # Acute: Sum of last 7 days
            acute = sum([daily_tonnage.get(dates[j], 0) for j in range(i-6, i+1)])
            
            # Chronic: Average of last 28 days
            chronic_sum = sum([daily_tonnage.get(dates[j], 0) for j in range(i-27, i+1)])
            chronic_avg = chronic_sum / 4.0 # 4 weeks
            
            ratio = (acute / chronic_avg) if chronic_avg > 0 else 0
            
            acwr_dates.append(datetime.strptime(target_date, "%Y-%m-%d").timestamp())
            acwr_values.append(ratio)
            
        return acwr_dates, acwr_values

    def _render_acwr(self, data):
        self.graph_acwr.clearPlots()
        timestamps, ratios = data
        if not timestamps: return
        
        pen = pg.mkPen(color='#2196F3', width=3)
        self.graph_acwr.plot(timestamps, ratios, pen=pen, name="ACWR")
        self.graph_acwr.setYRange(0, 2.5)

    # ---------------------------------------------------------
    # TAB 2: MYOFASCIAL SLINGS
    # ---------------------------------------------------------
    def _setup_slings_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        info = QLabel(
            "<b>Functional Sling Balance</b><br>"
            "Analyzes your active program to ensure fascial kinetic chains are balanced, preventing postural dysfunctions."
        )
        layout.addWidget(info)
        
        self.graph_slings = pg.PlotWidget()
        self.graph_slings.setBackground('#1e1e1e')
        layout.addWidget(self.graph_slings)
        self.tabs.addTab(tab, "Myofascial Slings")

    def _fetch_sling_data(self):
        volume_map = WorkoutDatabaseManager.get_active_program_volume(self.current_user_id)
        
        # Simplified Clinical Sling Definitions
        sling_definitions = {
            "Posterior Oblique (POS)\nLats & Glutes": ['latissimus', 'glutes', 'upper-back'],
            "Anterior Oblique (AOS)\nObliques & Push Chain": ['abs', 'obliques', 'core', 'chest', 'shoulders'],
            "Deep Longitudinal (DLS)\nErectors & Hamstrings": ['lower-back', 'hamstrings', 'calves'],
            "Lateral Sling (LS)\nGlute Med & Core": ['glutes', 'core']
        }
        
        sling_volumes = {k: 0 for k in sling_definitions.keys()}
        
        for muscle, volume in volume_map.items():
            muscle_slug = muscle.lower().replace(' ', '-')
            for sling_name, muscles in sling_definitions.items():
                if muscle_slug in muscles:
                    sling_volumes[sling_name] += volume
                    
        return sling_volumes

    def _render_slings(self, sling_volumes):
        self.graph_slings.clear()
        
        names = list(sling_volumes.keys())
        volumes = list(sling_volumes.values())
        x = range(1, len(names) + 1)
        
        # Setup custom X-axis text ticks
        ticks = [list(zip(x, names))]
        axis = self.graph_slings.getAxis('bottom')
        axis.setTicks(ticks)
        
        # Plot Bar Graph
        bg = pg.BarGraphItem(x=x, height=volumes, width=0.6, brush='#9C27B0')
        self.graph_slings.addItem(bg)
        self.graph_slings.setLabel('left', "Total Active Program Sets", color="white")