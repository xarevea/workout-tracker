from PyQt6.QtWidgets import QPushButton

def create_sidebar_button(text: str) -> QPushButton:
    """Creates a standardized, styled button for the sidebar."""
    btn = QPushButton(text)
    btn.setStyleSheet("""
        QPushButton {
            padding: 10px;
            font-size: 16px;
            text-align: left;
            background: transparent;
            border: none;
            color: #E0E0E0;
        }
        QPushButton:hover {
            background-color: #3d3d3d;
            border-radius: 5px;
        }
        QPushButton:checked {
            background-color: #2196F3;
            color: white;
            font-weight: bold;
            border-radius: 5px;
        }
    """)
    btn.setCheckable(True)
    return btn

def add_button_above_stretch(layout, button):
    # Find the index of the last item in the layout
    last_item_index = layout.count() - 1
    
    # Check if the last item is a stretch (QSpacerItem)
    if layout.itemAt(last_item_index) and layout.itemAt(last_item_index).spacerItem():
        layout.insertWidget(last_item_index, button)
    else:
        # Fallback to appending if no stretch currently exists
        layout.addWidget(button)
        layout.addStretch()