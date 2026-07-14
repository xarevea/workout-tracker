from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush
from PyQt6.QtCore import Qt, QRectF

class BarbellVisualizer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(150)
        self.left_loadout = []
        self.right_loadout = []
        self.is_barbell = True

        self.color_map = {
            55.0: QColor("#F44336"), 45.0: QColor("#2196F3"), 35.0: QColor("#FFEB3B"),
            25.0: QColor("#4CAF50"), 10.0: QColor("#FFFFFF"), 5.0:  QColor("#9E9E9E"), 2.5:  QColor("#424242")
        }

    def set_loadout(self, plates: tuple, is_barbell: bool = True):
        self.is_barbell = is_barbell
        if plates and len(plates) == 2:
            self.left_loadout = sorted(plates[0], reverse=True)
            self.right_loadout = sorted(plates[1], reverse=True)
        else:
            self.left_loadout, self.right_loadout = [], []
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        center_x = self.width() / 2
        center_y = self.height() / 2

        if not self.left_loadout and not self.right_loadout:
            painter.setPen(QColor("#888888"))
            painter.setFont(painter.font())
            painter.drawText(int(center_x - 30), int(center_y - 30), "Empty Bar" if self.is_barbell else "Bodyweight")
            return

        if self.is_barbell:
            shaft_half_width = 80
            sleeve_height = 14
            total_bar_width = self.width() - 40
            bar_rect = QRectF(20, center_y - (sleeve_height / 2), total_bar_width, sleeve_height)
            painter.setBrush(QBrush(QColor("#555555")))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(bar_rect, 3, 3)

            painter.setBrush(QBrush(QColor("#777777")))
            painter.setPen(QPen(QColor("#111111"), 1))
            painter.drawRect(QRectF(center_x - shaft_half_width - 15, center_y - 20, 15, 40))
            painter.drawRect(QRectF(center_x + shaft_half_width, center_y - 20, 15, 40))

            current_left_x = center_x - shaft_half_width - 15 - 2
            current_right_x = center_x + shaft_half_width + 15 + 2

            def draw_plate(x, plate, is_left):
                plate_color = self.color_map.get(plate, QColor("#333333"))

                if plate >= 35.0: p_height, p_width = 80, 18
                elif plate >= 25.0: p_height, p_width = 60, 14
                elif plate >= 10.0: p_height, p_width = 45, 12
                else: p_height, p_width = 30, 8

                rect_x = x - p_width if is_left else x
                rect = QRectF(rect_x, center_y - (p_height / 2), p_width, p_height)

                painter.setBrush(QBrush(plate_color))
                painter.setPen(QPen(QColor("#111111"), 1))
                painter.drawRoundedRect(rect, 2, 2)

                if p_width >= 12:
                    painter.setPen(QColor("#000000") if plate in [10.0, 35.0] else QColor("#FFFFFF"))
                    font = painter.font()
                    font.setPixelSize(9)
                    font.setBold(True)
                    painter.setFont(font)
                    txt = str(int(plate) if plate.is_integer() else plate)
                    painter.save()
                    trans_x = rect_x + (p_width / 2) + 4
                    painter.translate(trans_x, center_y + (p_height / 2) - 5)
                    painter.rotate(-90)
                    painter.drawText(0, 0, txt)
                    painter.restore()

                return p_width + 2

            for plate in self.left_loadout:
                current_left_x -= draw_plate(current_left_x, plate, is_left=True)

            for plate in self.right_loadout:
                current_right_x += draw_plate(current_right_x, plate, is_left=False)

        else:
            # NON-BARBELL: Draw a vertical chain/pin in the center
            painter.setBrush(QBrush(QColor("#555555")))
            painter.setPen(QPen(QColor("#111111"), 1))
            painter.drawRect(QRectF(center_x - 5, center_y - 60, 10, 120))

            # Stack right_loadout plates vertically on the pin
            current_y = center_y - 50
            for plate in self.right_loadout:
                plate_color = self.color_map.get(plate, QColor("#333333"))

                # Flip width and height for vertical stacking
                if plate >= 35.0: p_width, p_height = 80, 18
                elif plate >= 25.0: p_width, p_height = 60, 14
                elif plate >= 10.0: p_width, p_height = 45, 12
                else: p_width, p_height = 30, 8

                rect = QRectF(center_x - (p_width / 2), current_y, p_width, p_height)
                painter.setBrush(QBrush(plate_color))
                painter.drawRoundedRect(rect, 2, 2)

                if p_height >= 12:
                    painter.setPen(QColor("#000000") if plate in [10.0, 35.0] else QColor("#FFFFFF"))
                    font = painter.font()
                    font.setPixelSize(9)
                    font.setBold(True)
                    painter.setFont(font)
                    txt = str(int(plate) if plate.is_integer() else plate)
                    painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, txt)

                current_y += (p_height + 2)