# ui/components/minimap.py
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt

class WorkoutMinimap(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.nodes = []

    def load_workout(self, exercises: list[str]):
        """Clears old nodes and loads the new exercise list."""
        # 1. DESTROY OLD WIDGETS (Fixes the duplication bug)
        for i in reversed(range(self.layout.count())):
            item = self.layout.itemAt(i)
            if item.widget():
                item.widget().setParent(None)
        
        self.nodes.clear()

        # 2. POPULATE NEW WIDGETS
        for i, ex in enumerate(exercises):
            lbl = QLabel(f"{i+1}. {ex}")
            lbl.setStyleSheet("color: gray; padding: 5px; font-size: 14px;")
            self.layout.addWidget(lbl)
            self.nodes.append(lbl)

    def set_active_node(self, index: int):
        """Highlights the current exercise and strikes through completed ones."""
        for i, node in enumerate(self.nodes):
            if i == index:
                # Active
                node.setStyleSheet("color: #4CAF50; font-weight: bold; padding: 5px; background-color: #2d2d2d; border-radius: 5px; font-size: 14px;")
            elif i < index:
                # Completed
                node.setStyleSheet("color: #888888; text-decoration: line-through; padding: 5px; font-size: 14px;")
            else:
                # Upcoming
                node.setStyleSheet("color: white; padding: 5px; font-size: 14px;")