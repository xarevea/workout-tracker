import json
import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy
from PyQt6.QtSvgWidgets import QSvgWidget
from PyQt6.QtCore import Qt

class MuscleMapper:
    """Utility class mapping high-level logical groups to specific SVG muscle slugs."""
    
    # Mappings allowing group highlighting by region
    REGION_MAP = {
        "Chest": ["chest"],
        "Back": ["latissimus", "trapezius", "lower-back"],
        "Core": ["abs", "obliques"],
        "Arms": ["biceps", "triceps", "forearm"],
        "Shoulders": ["deltoids"],
        "Legs": ["quadriceps", "hamstring", "calves", "gluteal", "adductors"],
    }
    
    @staticmethod
    def get_color(sets: float) -> str:
        """Standard weekly volume targets for hypertrophy."""
        if sets == 0: return '#333333'      # Unused (Dark Gray)
        elif sets < 8: return '#2196F3'     # Underworked (Blue)
        elif sets <= 20: return '#4CAF50'   # Optimal (Green)
        else: return '#F44336'              # Overworked (Red)

class AnatomicalHeatmap(QWidget):
    def __init__(self, parent=None, data_path='male_model_data.json'):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.setMinimumSize(300, 200) 
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Load parsed SVG data 
        if os.path.exists(data_path):
            with open(data_path, 'r', encoding='utf-8') as f:
                self.model_data = json.load(f)
        else:
            # Fallback structure if the json is missing
            self.model_data = {
                "front": {"border": "", "muscles": {}, "viewBox": "0 0 724 1448"}, 
                "back": {"border": "", "muscles": {}, "viewBox": "724 0 724 1448"}
            }
                
        svg_layout = QHBoxLayout()
        
        ant_layout = QVBoxLayout()
        ant_label = QLabel("Anterior")
        ant_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ant_label.setStyleSheet("color: #888888; font-size: 12px; font-weight: bold; text-transform: uppercase;")
        self.front_svg = QSvgWidget()
        # Ensure PyQt respects the SVG's internal aspect ratio request
        self.front_svg.renderer().setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)
        ant_layout.addWidget(ant_label)
        ant_layout.addWidget(self.front_svg)
        
        post_layout = QVBoxLayout()
        post_label = QLabel("Posterior")
        post_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        post_label.setStyleSheet("color: #888888; font-size: 12px; font-weight: bold; text-transform: uppercase;")
        self.back_svg = QSvgWidget()
        self.back_svg.renderer().setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)
        post_layout.addWidget(post_label)
        post_layout.addWidget(self.back_svg)
        
        svg_layout.addLayout(ant_layout)
        svg_layout.addLayout(post_layout)
        self.layout.addLayout(svg_layout)

    def update_heatmap(self, volume_map: dict):
        """Translates the DB volume map into SVG colors."""
        
        # 1. Flatten into granular slugs
        slug_volume = {}
        for key, sets in volume_map.items():
            key_str = str(key).strip()
            
            # Check if this key is a high-level grouping
            matched_group = False
            for region, slugs in MuscleMapper.REGION_MAP.items():
                if key_str.lower() == region.lower():
                    for slug in slugs:
                        slug_volume[slug] = slug_volume.get(slug, 0) + sets
                    matched_group = True
                    break
            
            # If not a group, it's a direct slug (e.g., 'biceps', 'latissimus')
            if not matched_group:
                slug_volume[key_str.lower()] = slug_volume.get(key_str.lower(), 0) + sets

        # 2. Map calculated sets to SVG colors
        slug_colors = {slug: MuscleMapper.get_color(sets) for slug, sets in slug_volume.items()}

        # 3. Generate SVGs
        front_xml = self._generate_svg('front', slug_colors)
        back_xml = self._generate_svg('back', slug_colors)
        
        self.front_svg.load(front_xml.encode('utf-8'))
        self.back_svg.load(back_xml.encode('utf-8'))

    def _generate_svg(self, side: str, slug_colors: dict) -> str:
        data = self.model_data[side]
        viewBox = data['viewBox']
        border_path = data['border']
        muscles = data['muscles']
        
        svg_parts = [f'<svg viewBox="{viewBox}" preserveAspectRatio="xMidYMid meet" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">']
        
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