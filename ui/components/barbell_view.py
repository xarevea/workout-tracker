# ========================================
# FILE PATH: ui/components/barbell_view.py
# ========================================
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush
from PyQt6.QtCore import Qt, QRectF

class BarbellVisualizer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(100)
        self.loadout = []

        # Standard Powerlifting Color Codes
        self.color_map = {
            55.0: QColor("#F44336"), # Red
            45.0: QColor("#2196F3"), # Blue
            35.0: QColor("#FFEB3B"), # Yellow
            25.0: QColor("#4CAF50"), # Green
            10.0: QColor("#FFFFFF"), # White
            5.0:  QColor("#9E9E9E"), # Light Gray
            2.5:  QColor("#424242"), # Dark Gray
        }

    def set_loadout(self, plates: list):
        self.loadout = sorted(plates, reverse=True)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        center_x = self.width() / 2
        center_y = self.height() / 2
        shaft_half_width = 80 # Space between the collars where the user's head goes
        
        # 1. Draw the Barbell Shaft & Sleeves (Dark Gray)
        # We draw one long rectangle across the screen
        sleeve_height = 14
        total_bar_width = self.width() - 40
        bar_rect = QRectF(20, center_y - (sleeve_height / 2), total_bar_width, sleeve_height)
        painter.setBrush(QBrush(QColor("#555555")))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(bar_rect, 3, 3)

        # 2. Draw the Inner Collars
        painter.setBrush(QBrush(QColor("#777777")))
        painter.setPen(QPen(QColor("#111111"), 1))
        # Left Collar
        painter.drawRect(QRectF(center_x - shaft_half_width - 15, center_y - 20, 15, 40))
        # Right Collar
        painter.drawRect(QRectF(center_x + shaft_half_width, center_y - 20, 15, 40))
        
        if not self.loadout:
            painter.setPen(QColor("#888888"))
            painter.setFont(painter.font())
            painter.drawText(int(center_x - 30), int(center_y - 30), "Empty Bar")
            return

        # Start pointers just outside the collars
        current_left_x = center_x - shaft_half_width - 15 - 2 
        current_right_x = center_x + shaft_half_width + 15 + 2

        # 3. Draw the Plates Symmetrically Outward
        for plate in self.loadout:
            plate_color = self.color_map.get(plate, QColor("#333333"))
            
            # Sizing logic
            if plate >= 35.0:
                p_height, p_width = 80, 18
            elif plate >= 25.0:
                p_height, p_width = 60, 14
            elif plate >= 10.0:
                p_height, p_width = 45, 12
            else:
                p_height, p_width = 30, 8

            # Calculate exact rects for left and right
            left_rect = QRectF(current_left_x - p_width, center_y - (p_height / 2), p_width, p_height)
            right_rect = QRectF(current_right_x, center_y - (p_height / 2), p_width, p_height)
            
            painter.setBrush(QBrush(plate_color))
            painter.setPen(QPen(QColor("#111111"), 1)) 
            
            # Draw Both Plates
            painter.drawRoundedRect(left_rect, 2, 2)
            painter.drawRoundedRect(right_rect, 2, 2)
            
            # Draw Text on Both Plates
            if p_width >= 12:
                painter.setPen(QColor("#000000") if plate in [10.0, 35.0] else QColor("#FFFFFF"))
                font = painter.font()
                font.setPixelSize(9)
                font.setBold(True)
                painter.setFont(font)
                
                txt = str(int(plate) if plate.is_integer() else plate)
                
                # Left side text
                painter.save()
                painter.translate(current_left_x - p_width + (p_width / 2) + 4, center_y + (p_height / 2) - 5)
                painter.rotate(-90)
                painter.drawText(0, 0, txt)
                painter.restore()

                # Right side text
                painter.save()
                painter.translate(current_right_x + (p_width / 2) + 4, center_y + (p_height / 2) - 5)
                painter.rotate(-90)
                painter.drawText(0, 0, txt)
                painter.restore()

            # Shift the pointers outward for the next plate
            current_left_x -= (p_width + 2)
            current_right_x += (p_width + 2)