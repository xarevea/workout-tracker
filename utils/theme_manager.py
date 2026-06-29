from PyQt6.QtWidgets import QApplication

THEMES = {
    "catppuccin": {
        "bg": "#24273a", "surface": "#363a4f", "surface2": "#494d64",
        "text": "#cad3f5", "primary": "#8aadf4", "border": "#181825"
    },
    "nord": {
        "bg": "#2e3440", "surface": "#3b4252", "surface2": "#434c5e",
        "text": "#d8dee9", "primary": "#81a1c1", "border": "#2e3440"
    }
}

def apply_theme(app: QApplication, theme_name: str = "catppuccin"):
    colors = THEMES.get(theme_name, THEMES["catppuccin"])
    
    qss = f"""
    QMainWindow, QWidget {{
        background-color: {colors['bg']};
        color: {colors['text']};
    }}
    QGroupBox {{
        background-color: {colors['surface']};
        border: 1px solid {colors['border']};
        border-radius: 8px;
        margin-top: 16px; 
    }}
    QGroupBox::title {{
        subcontrol-origin: margin; left: 12px; top: -8px; 
        color: {colors['primary']}; background-color: {colors['surface']};
        padding: 0 4px; border-radius: 4px; font-weight: bold;
    }}
    QPushButton {{
        background-color: {colors['surface2']}; border: none; 
        border-radius: 6px; padding: 8px 16px; color: {colors['text']}; font-weight: bold;
    }}
    QPushButton:hover {{ background-color: {colors['primary']}; color: {colors['bg']}; }}
    QSpinBox, QDoubleSpinBox, QComboBox, QSlider {{
        background-color: {colors['bg']}; border: 1px solid {colors['border']};
        border-radius: 4px; padding: 6px; color: {colors['text']};
    }}
    """
    app.setStyleSheet(qss)