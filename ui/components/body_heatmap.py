import json
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy, 
)
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtGui import QPainter, QImage, QColor
from PyQt6.QtCore import Qt, QPointF, QRectF, pyqtSignal

class AspectRatioSvgWidget(QWidget):
    """
    A custom widget that renders SVG data using a QPainter. 
    Includes exact path click detection via an off-screen color hitmap.
    """
    
    # Signal emitted when a valid path is clicked: (element_id, region)
    elementClicked = pyqtSignal(str, str) 

    def __init__(self, parent=None):
        super().__init__(parent)
        self.svg_renderer = QSvgRenderer()
        self.hitmap_renderer = QSvgRenderer() # Hidden renderer for exact click detection
        
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(50, 100)

        self._click_map = {}
        self._color_to_slug = {}
        self._draw_rect = QRectF()

    def load(self, visual_bytes, hitmap_bytes, color_to_slug):
        self.svg_renderer.load(visual_bytes)
        self.hitmap_renderer.load(hitmap_bytes)
        self._color_to_slug = color_to_slug
        
        self.update()

        # Update event handler based on available elements
        self._click_map.clear()
        for region, slugs in MuscleMapper.REGION_MAP.items():
            for element_id in slugs:
                if self.svg_renderer.elementExists(element_id):
                    self._click_map[element_id] = region

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
            draw_height = self.height()
            draw_width = draw_height * svg_ratio
            x = (self.width() - draw_width) / 2
            y = 0.0
        else:
            draw_width = self.width()
            draw_height = draw_width / svg_ratio
            x = 0.0
            y = (self.height() - draw_height) / 2
            
        # Store for hitmap mapping in mousePressEvent
        self._draw_rect = QRectF(x, y, draw_width, draw_height)
        self.svg_renderer.render(painter, self._draw_rect)

    def mousePressEvent(self, event):
        """Detect pixel-perfect click using the hidden hitmap."""
        if not self.hitmap_renderer.isValid() or self._draw_rect.isNull():
            return super().mousePressEvent(event)

        pos = event.position()
        x, y = int(pos.x()), int(pos.y())

        # Render the hitmap into a transparent QImage exactly matching the widget size
        img = QImage(self.size(), QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(img)
        # CRITICAL: Disable antialiasing so edge pixels don't blend into unknown colors
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False) 
        self.hitmap_renderer.render(painter, self._draw_rect)
        painter.end()

        # Check bounds and get pixel color
        if 0 <= x < img.width() and 0 <= y < img.height():
            color = img.pixelColor(x, y)
            
            # If the pixel isn't fully transparent, we hit a mapped shape
            if color.alpha() == 255: 
                hex_color = color.name().upper() # Format: #RRGGBB
                element_id = self._color_to_slug.get(hex_color)
                
                if element_id and element_id in self._click_map:
                    region = self._click_map[element_id]
                    self.elementClicked.emit(element_id, region)
                    
        super().mousePressEvent(event)


class MuscleMapper:
    REGION_MAP = {
        "Chest": ["chest"],
        "Back": ["upper-back", "latissimus", "trapezius", "lower-back", "back"],
        "Core": ["abs", "obliques", "core"],
        "Arms": ["biceps", "triceps", "forearms", "arms"],
        "Shoulders": ["deltoids", "shoulders"],
        "Legs": ["quadriceps", "hamstrings", "calves", "glutes", "adductors", "legs"],
    }
    
    @staticmethod
    def get_color(sets: float) -> str:
        if sets == 0: 
            return '#333333'      
        elif sets < 10: 
            return '#2196F3'
        elif sets <= 20: 
            return '#4CAF50'
        else: 
            return '#F44336'   

    @staticmethod
    def get_ui_muscle_list(include_empty=True) -> list:
        """
        Generates a single-source-of-truth list for all UI dropdowns.
        Extracts both broad regions (e.g. 'Back') and specific muscles (e.g. 'Upper Back').
        """
        regions = list(MuscleMapper.REGION_MAP.keys())
        muscles = []
        for slugs in MuscleMapper.REGION_MAP.values():
            muscles.extend([s.replace('-', ' ').title() for s in slugs])
        
        # Merge, remove duplicates, and sort alphabetically
        combined = sorted(list(set(regions + muscles)))
        if include_empty:
            combined.insert(0, "")
        return combined     

class AnatomicalHeatmap(QWidget):
    
    # Top-level signal for easy app integration: (element_id, region)
    regionClicked = pyqtSignal(str, str) 

    def __init__(self, parent=None, data_path='male_model_data.json'):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
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
        ant_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        ant_layout.addWidget(ant_label)
        self.front_svg = AspectRatioSvgWidget()
        ant_layout.addWidget(self.front_svg, stretch=1) 
        
        # Posterior
        post_layout = QVBoxLayout()
        post_label = QLabel("Posterior")
        post_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        post_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        post_layout.addWidget(post_label)
        self.back_svg = AspectRatioSvgWidget()
        post_layout.addWidget(self.back_svg, stretch=1) 
        
        svg_layout.addLayout(ant_layout)
        svg_layout.addLayout(post_layout)
        self.layout.addLayout(svg_layout)

        # Connect the internal widget signals to the top-level class signal
        self.front_svg.elementClicked.connect(self.regionClicked.emit)
        self.back_svg.elementClicked.connect(self.regionClicked.emit)

    def update_heatmap(self, volume_map: dict):
        slug_volume = {}
        for key, sets in volume_map.items():
            key_str = str(key).strip().lower()
            
            is_direct_slug = False
            for region, slugs in MuscleMapper.REGION_MAP.items():
                if key_str in slugs:
                    slug_volume[key_str] = slug_volume.get(key_str, 0) + sets
                    is_direct_slug = True
                    break
                    
            if is_direct_slug:
                continue
                
            matched_group = False
            for region, slugs in MuscleMapper.REGION_MAP.items():
                if key_str == region.lower():
                    for slug in slugs:
                        slug_volume[slug] = slug_volume.get(slug, 0) + sets
                    matched_group = True
                    break
            
            if not matched_group:
                slug_volume[key_str] = slug_volume.get(key_str, 0) + sets

        slug_colors = {slug: MuscleMapper.get_color(sets) for slug, sets in slug_volume.items()}

        # Gather all unique slugs to build a hitmap dictionary
        all_slugs = set(self.model_data['front']['muscles'].keys()) | set(self.model_data['back']['muscles'].keys())
        
        color_to_slug = {}
        slug_to_hitmap_color = {}
        
        for i, slug in enumerate(all_slugs):
            # Generate a unique hex color for each slug, starting at #000001
            hex_color = f"#{i+1:06X}" 
            slug_to_hitmap_color[slug] = hex_color
            color_to_slug[hex_color] = slug

        # Generate both the visual SVG and hidden hitmap SVG
        front_vis, front_hit = self._generate_svgs('front', slug_colors, slug_to_hitmap_color)
        back_vis, back_hit = self._generate_svgs('back', slug_colors, slug_to_hitmap_color)
        
        self.front_svg.load(front_vis.encode('utf-8'), front_hit.encode('utf-8'), color_to_slug)
        self.back_svg.load(back_vis.encode('utf-8'), back_hit.encode('utf-8'), color_to_slug)

    def _generate_svgs(self, side: str, slug_colors: dict, slug_to_hitmap_color: dict):
        """Returns a tuple of (visual_xml, hitmap_xml)."""
        data = self.model_data[side]
        viewBox = data['viewBox']
        border_path = data['border']
        muscles = data['muscles']
        
        vis_parts = [f'<svg viewBox="{viewBox}" xmlns="http://www.w3.org/2000/svg">']
        hit_parts = [f'<svg viewBox="{viewBox}" xmlns="http://www.w3.org/2000/svg">']

        for slug, muscle_data in muscles.items():
            v_color = slug_colors.get(slug, '#333333') 
            h_color = slug_to_hitmap_color.get(slug, '#FFFFFF')
            
            vis_parts.append(f'<g id="{slug}" fill="{v_color}">')
            hit_parts.append(f'<g id="{slug}" fill="{h_color}">')
            
            paths = muscle_data.get('left', []) + muscle_data.get('right', [])
            for path in paths:
                path_str = f'  <path d="{path}" />'
                vis_parts.append(path_str)
                hit_parts.append(path_str)
                
            vis_parts.append('</g>')
            hit_parts.append('</g>')
            
        if border_path:
            # Only add the border to the visual SVG so it doesn't intercept clicks
            vis_parts.append(f'<path d="{border_path}" fill="none" stroke="#1c1c1c" stroke-width="2" />')
            
        vis_parts.append('</svg>')
        hit_parts.append('</svg>')
        
        return "\n".join(vis_parts), "\n".join(hit_parts)