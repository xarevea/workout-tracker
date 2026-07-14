# ui/components/minimap.py
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea
from PyQt6.QtCore import Qt, pyqtSignal

class ClickableLabel(QLabel):
    clicked = pyqtSignal(int)

    def __init__(self, index, text, parent=None):
        super().__init__(text, parent)
        self.index = index
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):
        self.clicked.emit(self.index)
        super().mousePressEvent(event)

class WorkoutMinimap(QWidget):
    nodeClicked = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.container = QWidget()
        self.container.setStyleSheet("background: transparent;")
        self.inner_layout = QVBoxLayout(self.container)
        self.inner_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.scroll_area.setWidget(self.container)
        self.layout.addWidget(self.scroll_area)

    def update_map(self, controller):
        for i in reversed(range(self.inner_layout.count())):
            item = self.inner_layout.itemAt(i)
            if item.widget():
                item.widget().setParent(None)

        if not controller.exercises: return

        active_task = controller.get_current_task()
        active_ex_name = active_task['exercise']['name'] if active_task else None

        logs_by_ex = {}
        for log in controller.session_logs:
            logs_by_ex.setdefault(log['exercise'], []).append(log)

        queue_by_ex = {}
        for i, q in enumerate(controller.queue):
            if i >= controller.queue_index:
                queue_by_ex.setdefault(q['exercise']['name'], []).append((i, q))

        for i, ex in enumerate(controller.exercises):
            ex_name = ex['name']
            is_active = (ex_name == active_ex_name)
            is_completed = (ex_name not in queue_by_ex) and not is_active

            # INTERACTIVE LABEL
            lbl = ClickableLabel(i, f"{i+1}. {ex_name}")
            lbl.clicked.connect(self.nodeClicked.emit)

            if is_active:
                lbl.setStyleSheet("color: #4CAF50; font-weight: bold; padding: 5px; background-color: #2d2d2d; border-radius: 5px; font-size: 14px;")
            elif is_completed:
                lbl.setStyleSheet("color: #888888; text-decoration: line-through; padding: 5px; font-size: 14px;")
            else:
                lbl.setStyleSheet("color: white; padding: 5px; font-size: 14px;")

            self.inner_layout.addWidget(lbl)

            if is_active:
                for log in logs_by_ex.get(ex_name, []):
                    prefix = "Warm-up" if log.get('is_warmup') else f"Set {log['set']}"
                    t = "s" if ex.get('tracks_time') else " reps"
                    txt = f"   ✓ {prefix}: {log['reps']}{t} @ {log['weight']} lbs"

                    sub_lbl = QLabel(txt)
                    sub_lbl.setStyleSheet("color: #888888; text-decoration: line-through; font-size: 12px;")
                    self.inner_layout.addWidget(sub_lbl)

                for q_i, q_task in queue_by_ex.get(ex_name, []):
                    prefix = "Warm-up" if q_task.get('is_warmup') else f"Set {q_task['set_number']}"
                    t = "s" if q_task['exercise'].get('tracks_time') else " reps"
                    txt = f"   • {prefix}: {q_task['target_reps']}{t} @ {q_task['target_weight']} lbs"

                    sub_lbl = QLabel(txt)
                    if q_i == controller.queue_index:
                        sub_lbl.setStyleSheet("color: #4CAF50; font-weight: bold; font-size: 12px;")
                    else:
                        sub_lbl.setStyleSheet("color: #b0b0b0; font-size: 12px;")
                    self.inner_layout.addWidget(sub_lbl)