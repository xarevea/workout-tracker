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