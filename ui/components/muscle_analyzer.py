# ui/components/muscle_analyzer.py
from PyQt6.QtWidgets import QDialog, QVBoxLayout
import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np

from core.db_operations import WorkoutDatabaseManager
from ui.components.body_heatmap import MuscleMapper

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
        exercises = WorkoutDatabaseManager.get_routine_exercises(template_id)
        
        volume_map = {region: 0 for region in MuscleMapper.REGION_MAP.keys()}

        for ex in exercises:
            sets = ex['target_sets']
            primary = ex['primary_muscle']
            
            if primary:
                primary_title = primary.title()
                if primary_title in volume_map:
                    # It's already a top-level region (e.g. "Chest")
                    volume_map[primary_title] += sets
                else:
                    # Find which region this specific muscle belongs to
                    for region, slugs in MuscleMapper.REGION_MAP.items():
                        if primary.lower().replace(' ', '-') in slugs:
                            volume_map[region] += sets
                            break
                            
            if ex['secondary_muscles']:
                secondaries = [s.strip() for s in ex['secondary_muscles'].split(',')]
                for sec in secondaries:
                    sec_title = sec.title()
                    if sec_title in volume_map:
                        volume_map[sec_title] += (sets * 0.5)
                    else:
                        for region, slugs in MuscleMapper.REGION_MAP.items():
                            if sec.lower().replace(' ', '-') in slugs:
                                volume_map[region] += (sets * 0.5)
                                break

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