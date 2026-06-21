# ui/components/minimap.py
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame
from PyQt6.QtCore import Qt

class WorkoutMinimap(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(8)
        
        title = QLabel("Workout Flow")
        title.setStyleSheet("font-weight: bold; font-size: 14px; color: #888888;")
        self.layout.addWidget(title)
        
        self.nodes = []

    def load_workout(self, exercises: list[str]):
        """Populates the minimap with exercise names."""
        self._clear_layout()
        
        for index, exercise in enumerate(exercises):
            node = QLabel(f"{index + 1}. {exercise}")
            node.setPadding = 5
            # Default style: Upcoming (muted)
            node.setStyleSheet("color: #666666; border-left: 3px solid transparent; padding-left: 5px;")
            self.layout.addWidget(node)
            self.nodes.append(node)
            
        self.layout.addStretch() # Push everything to the top

    def set_active_node(self, index: int):
        """Updates UI to show the current active exercise."""
        for i, node in enumerate(self.nodes):
            if i < index:
                # Completed
                node.setStyleSheet("color: #4CAF50; border-left: 3px solid #4CAF50; padding-left: 5px;")
            elif i == index:
                # Active
                node.setStyleSheet("color: #FFFFFF; font-weight: bold; border-left: 3px solid #2196F3; padding-left: 5px;")
            else:
                # Upcoming
                node.setStyleSheet("color: #666666; border-left: 3px solid transparent; padding-left: 5px;")

    def _clear_layout(self):
        for i in reversed(range(self.layout.count())): 
            widget = self.layout.itemAt(i).widget()
            if widget is not None and widget.__class__ is not QLabel:
                widget.setParent(None)
        self.nodes.clear()