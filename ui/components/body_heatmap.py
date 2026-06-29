import json
import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtGui import QPainter
from PyQt6.QtCore import Qt, QRectF

class AspectRatioSvgWidget(QWidget):
    """
    A custom widget that renders SVG data using a QPainter. 
    This entirely bypasses PyQt's native QSvgWidget squishing behavior 
    and guarantees the aspect ratio is maintained regardless of the parent layout.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.svg_renderer = QSvgRenderer()
        # Allow the widget to peacefully expand or shrink without demanding massive space
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(50, 100)

    def load(self, byte_array):
        self.svg_renderer.load(byte_array)
        self.update() # Trigger a repaint

    def paintEvent(self, event):
        if not self.svg_renderer.isValid():
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        viewBox = self.svg_renderer.viewBoxF()
        if viewBox.isNull():
            return
            
        svg_ratio = viewBox.width() / viewBox.height()
        widget_ratio = self.width() / self.height()
        
        # Calculate maximum centered bounding box that perfectly preserves ratio
        if widget_ratio > svg_ratio:
            # Widget is wider than needed; bind to height
            draw_height = self.height()
            draw_width = draw_height * svg_ratio
            x = (self.width() - draw_width) / 2
            y = 0.0
        else:
            # Widget is taller than needed; bind to width
            draw_width = self.width()
            draw_height = draw_width / svg_ratio
            x = 0.0
            y = (self.height() - draw_height) / 2
            
        draw_rect = QRectF(x, y, draw_width, draw_height)
        self.svg_renderer.render(painter, draw_rect)


class MuscleMapper:
    """Utility class mapping high-level logical groups to specific SVG muscle slugs."""
    
    REGION_MAP = {
        "Chest": ["chest"],
        "Back": ["upper-back", "latissimus", "trapezius", "lower-back"],
        "Core": ["abs", "obliques"],
        "Arms": ["biceps", "triceps", "forearm"],
        "Shoulders": ["deltoids"],
        "Legs": ["quadriceps", "hamstring", "calves", "gluteal", "adductors"],
    }
    
    @staticmethod
    def get_color(sets: float) -> str:
        if sets == 0: return '#333333'      
        elif sets < 8: return '#2196F3'     
        elif sets <= 20: return '#4CAF50'   
        else: return '#F44336'              

class AnatomicalHeatmap(QWidget):
    def __init__(self, parent=None, data_path='male_model_data.json'):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # Removed the hardcoded maximum height. The custom renderer won't crush 
        # the dashboard charts anymore, allowing this to grow properly in Active Tracker.
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        if os.path.exists(data_path):
            with open(data_path, 'r', encoding='utf-8') as f:
                self.model_data = json.load(f)
        else:
            self.model_data = {
                "front": {"border": "", "muscles": {}, "viewBox": "0 0 724 1448"}, 
                "back": {"border": "", "muscles": {}, "viewBox": "724 0 724 1448"}
            }
                
        svg_layout = QHBoxLayout()
        
        # Anterior
        ant_layout = QVBoxLayout()
        ant_label = QLabel("Anterior")
        ant_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ant_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum) # Stop label from stretching
        ant_layout.addWidget(ant_label)
        self.front_svg = AspectRatioSvgWidget() # Use the custom class
        ant_layout.addWidget(self.front_svg, stretch=1) 
        
        # Posterior
        post_layout = QVBoxLayout()
        post_label = QLabel("Posterior")
        post_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        post_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        post_layout.addWidget(post_label)
        self.back_svg = AspectRatioSvgWidget() # Use the custom class
        post_layout.addWidget(self.back_svg, stretch=1) 
        
        svg_layout.addLayout(ant_layout)
        svg_layout.addLayout(post_layout)
        self.layout.addLayout(svg_layout)

    def update_heatmap(self, volume_map: dict):
        slug_volume = {}
        for key, sets in volume_map.items():
            key_str = str(key).strip().lower()
            
            # First, check if the key is already a direct slug (like "latissimus" or "chest")
            is_direct_slug = False
            for region, slugs in MuscleMapper.REGION_MAP.items():
                if key_str in slugs:
                    slug_volume[key_str] = slug_volume.get(key_str, 0) + sets
                    is_direct_slug = True
                    break
                    
            if is_direct_slug:
                continue
                
            # Otherwise, see if it's a broad category (like "Back") and add all its slugs
            matched_group = False
            for region, slugs in MuscleMapper.REGION_MAP.items():
                if key_str == region.lower():
                    for slug in slugs:
                        slug_volume[slug] = slug_volume.get(slug, 0) + sets
                    matched_group = True
                    break
            
            # Fallback if nothing matches
            if not matched_group:
                slug_volume[key_str] = slug_volume.get(key_str, 0) + sets

        slug_colors = {slug: MuscleMapper.get_color(sets) for slug, sets in slug_volume.items()}

        front_xml = self._generate_svg('front', slug_colors)
        back_xml = self._generate_svg('back', slug_colors)
        
        self.front_svg.load(front_xml.encode('utf-8'))
        self.back_svg.load(back_xml.encode('utf-8'))

    def _generate_svg(self, side: str, slug_colors: dict) -> str:
        data = self.model_data[side]
        viewBox = data['viewBox']
        border_path = data['border']
        muscles = data['muscles']
        
        # Stripped Qt's preserveAspectRatio since we manually calculate it now
        svg_parts = [f'<svg viewBox="{viewBox}" xmlns="http://www.w3.org/2000/svg">']

        for slug, muscle_data in muscles.items():
            color = slug_colors.get(slug, '#333333') 
            svg_parts.append(f'<g id="{slug}" fill="{color}">')
            paths = muscle_data.get('left', []) + muscle_data.get('right', [])
            for path in paths:
                svg_parts.append(f'  <path d="{path}" />')
            svg_parts.append('</g>')
            
        if border_path:
            svg_parts.append(f'<path d="{border_path}" fill="none" stroke="#1c1c1c" stroke-width="2" />')
            
        svg_parts.append('</svg>')
        return "\n".join(svg_parts)