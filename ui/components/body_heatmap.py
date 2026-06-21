# ui/components/body_heatmap.py
import numpy as np
from PyQt6.QtWidgets import QWidget, QVBoxLayout
import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.patches as patches

class AnatomicalHeatmap(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        
        self.fig = Figure(figsize=(8, 5), dpi=100)
        self.fig.patch.set_facecolor('#1e1e1e')
        self.canvas = FigureCanvas(self.fig)
        layout.addWidget(self.canvas)
        layout.setContentsMargins(0, 0, 0, 0)

    def _get_color(self, sets):
        """Standard weekly volume targets for hypertrophy."""
        if sets == 0: return '#333333'      # Unused (Dark Gray)
        elif sets < 8: return '#2196F3'     # Underworked (Blue)
        elif sets <= 20: return '#4CAF50'   # Optimal (Green)
        else: return '#F44336'              # Overworked (Red)

    def update_heatmap(self, volume_map):
        self.fig.clear()
        
        # Two subplots: Anterior (Front) and Posterior (Back)
        ax_ant = self.fig.add_subplot(121)
        ax_post = self.fig.add_subplot(122)

        for ax in [ax_ant, ax_post]:
            ax.set_facecolor('#1e1e1e')
            ax.set_xlim(-1, 1)
            ax.set_ylim(-1, 1)
            ax.axis('off')

        ax_ant.set_title("Anterior (Front)", color='white', pad=10)
        ax_post.set_title("Posterior (Back)", color='white', pad=10)

        # --- DRAW ANTERIOR MUSCLES ---
        # Chest
        ax_ant.add_patch(patches.Ellipse((-0.25, 0.4), 0.4, 0.3, color=self._get_color(volume_map.get("Chest", 0))))
        ax_ant.add_patch(patches.Ellipse((0.25, 0.4), 0.4, 0.3, color=self._get_color(volume_map.get("Chest", 0))))
        ax_ant.text(0, 0.4, "Chest", color='white', ha='center', va='center', fontsize=8, fontweight='bold')

        # Core/Abs
        ax_ant.add_patch(patches.Rectangle((-0.3, -0.1), 0.6, 0.4, color=self._get_color(volume_map.get("Core", 0))))
        ax_ant.text(0, 0.1, "Core", color='white', ha='center', va='center', fontsize=8, fontweight='bold')

        # Quads
        ax_ant.add_patch(patches.Ellipse((-0.25, -0.5), 0.3, 0.6, color=self._get_color(volume_map.get("Quads", 0))))
        ax_ant.add_patch(patches.Ellipse((0.25, -0.5), 0.3, 0.6, color=self._get_color(volume_map.get("Quads", 0))))
        ax_ant.text(0, -0.5, "Quads", color='white', ha='center', va='center', fontsize=8, fontweight='bold')

        # Shoulders & Biceps
        ax_ant.add_patch(patches.Circle((-0.6, 0.5), 0.15, color=self._get_color(volume_map.get("Shoulders", 0))))
        ax_ant.add_patch(patches.Circle((0.6, 0.5), 0.15, color=self._get_color(volume_map.get("Shoulders", 0))))
        ax_ant.add_patch(patches.Ellipse((-0.65, 0.2), 0.2, 0.3, color=self._get_color(volume_map.get("Biceps", 0))))
        ax_ant.add_patch(patches.Ellipse((0.65, 0.2), 0.2, 0.3, color=self._get_color(volume_map.get("Biceps", 0))))

        # --- DRAW POSTERIOR MUSCLES ---
        # Back (Lats/Traps)
        back_poly = np.array([[-0.4, 0.6], [0.4, 0.6], [0.2, 0.0], [-0.2, 0.0]])
        ax_post.add_patch(patches.Polygon(back_poly, color=self._get_color(volume_map.get("Back", 0))))
        ax_post.text(0, 0.4, "Back", color='white', ha='center', va='center', fontsize=8, fontweight='bold')

        # Hamstrings & Glutes
        ax_post.add_patch(patches.Ellipse((-0.25, -0.4), 0.35, 0.5, color=self._get_color(volume_map.get("Hamstrings", 0))))
        ax_post.add_patch(patches.Ellipse((0.25, -0.4), 0.35, 0.5, color=self._get_color(volume_map.get("Hamstrings", 0))))
        ax_post.text(0, -0.4, "Hamstrings", color='white', ha='center', va='center', fontsize=8, fontweight='bold')

        # Calves
        ax_post.add_patch(patches.Ellipse((-0.25, -0.85), 0.2, 0.25, color=self._get_color(volume_map.get("Calves", 0))))
        ax_post.add_patch(patches.Ellipse((0.25, -0.85), 0.2, 0.25, color=self._get_color(volume_map.get("Calves", 0))))

        # Triceps
        ax_post.add_patch(patches.Ellipse((-0.65, 0.2), 0.2, 0.3, color=self._get_color(volume_map.get("Triceps", 0))))
        ax_post.add_patch(patches.Ellipse((0.65, 0.2), 0.2, 0.3, color=self._get_color(volume_map.get("Triceps", 0))))

        # Legend
        self.fig.legend(
            handles=[
                patches.Patch(color='#2196F3', label='Underworked (<8 sets)'),
                patches.Patch(color='#4CAF50', label='Optimal (8-20 sets)'),
                patches.Patch(color='#F44336', label='Overworked (>20 sets)')
            ],
            loc='lower center', ncol=3, facecolor='#2d2d2d', edgecolor='#555555', labelcolor='white'
        )

        self.fig.tight_layout()
        self.canvas.draw()