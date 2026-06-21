# ui/components/muscle_analyzer.py
from PyQt6.QtWidgets import QDialog, QVBoxLayout
import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np

from core.database import get_connection

class MuscleCoverageDialog(QDialog):
    def __init__(self, template_id, template_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Muscle Coverage Analysis: {template_name}")
        self.resize(600, 500)
        
        layout = QVBoxLayout(self)
        
        self.fig = Figure(figsize=(6, 5), dpi=100)
        self.fig.patch.set_facecolor('#1e1e1e')
        self.canvas = FigureCanvas(self.fig)
        layout.addWidget(self.canvas)
        
        self._analyze_coverage(template_id)

    def _analyze_coverage(self, template_id):
        conn = get_connection()
        cursor = conn.cursor()
        
        # Join the routine layout with the master exercise dictionary
        cursor.execute('''
            SELECT r.target_sets, e.primary_muscle, e.secondary_muscles
            FROM routine_exercises r
            JOIN exercises e ON r.exercise_name = e.name
            WHERE r.template_id = ?
        ''', (template_id,))
        
        exercises = cursor.fetchall()
        conn.close()

        # Tally the volume
        volume_map = {
            "Chest": 0, "Back": 0, "Quads": 0, "Hamstrings": 0, 
            "Calves": 0, "Shoulders": 0, "Biceps": 0, "Triceps": 0, "Core": 0
        }

        for ex in exercises:
            sets = ex['target_sets']
            
            # Primary gets 1.0x points per set
            if ex['primary_muscle'] in volume_map:
                volume_map[ex['primary_muscle']] += sets
                
            # Secondaries get 0.5x points per set
            if ex['secondary_muscles']:
                secondaries = [s.strip() for s in ex['secondary_muscles'].split(',')]
                for sec in secondaries:
                    if sec in volume_map:
                        volume_map[sec] += (sets * 0.5)

        self._plot_radar_chart(volume_map)

    def _plot_radar_chart(self, volume_map):
        ax = self.fig.add_subplot(111, polar=True)
        ax.set_facecolor('#1e1e1e')
        
        # Prepare data for Radar Chart
        categories = list(volume_map.keys())
        values = list(volume_map.values())
        
        # Radar charts require the data to "close the loop"
        values += values[:1]
        angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
        angles += angles[:1]

        # Plotting
        ax.plot(angles, values, color='#4CAF50', linewidth=2)
        ax.fill(angles, values, color='#4CAF50', alpha=0.4)
        
        # Styling
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories, color='white', size=10)
        ax.tick_params(axis='y', colors='#888888')
        ax.spines['polar'].set_color('#555555')
        
        self.fig.tight_layout()
        self.canvas.draw()