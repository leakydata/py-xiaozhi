from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.utils.config_manager import ConfigManager
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class ShortcutsSettingsWidget(QWidget):
    """
    Shortcut settings component.
    """

    # Signal definition
    settings_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = ConfigManager.get_instance()
        self.shortcuts_config = self.config.get_config("SHORTCUTS", {})
        self.init_ui()

    def init_ui(self):
        """
        Initialize UI.
        """
        layout = QVBoxLayout()

        # Enable shortcuts option
        self.enable_checkbox = QCheckBox("Enable global shortcuts")
        self.enable_checkbox.setChecked(self.shortcuts_config.get("ENABLED", True))
        self.enable_checkbox.toggled.connect(self.on_settings_changed)
        layout.addWidget(self.enable_checkbox)

        # Shortcut configuration group
        shortcuts_group = QGroupBox("Shortcut Configuration")
        shortcuts_layout = QVBoxLayout()

        # Create individual shortcut configuration widgets
        self.shortcut_widgets = {}

        # Push to talk
        self.shortcut_widgets["MANUAL_PRESS"] = self.create_shortcut_config(
            "Push to talk", self.shortcuts_config.get("MANUAL_PRESS", {})
        )
        shortcuts_layout.addWidget(self.shortcut_widgets["MANUAL_PRESS"])

        # Auto-dialogue
        self.shortcut_widgets["AUTO_TOGGLE"] = self.create_shortcut_config(
            "Auto-dialogue", self.shortcuts_config.get("AUTO_TOGGLE", {})
        )
        shortcuts_layout.addWidget(self.shortcut_widgets["AUTO_TOGGLE"])

        # Interrupt dialogue
        self.shortcut_widgets["ABORT"] = self.create_shortcut_config(
            "Interrupt dialogue", self.shortcuts_config.get("ABORT", {})
        )
        shortcuts_layout.addWidget(self.shortcut_widgets["ABORT"])

        # Toggle mode
        self.shortcut_widgets["MODE_TOGGLE"] = self.create_shortcut_config(
            "Toggle mode", self.shortcuts_config.get("MODE_TOGGLE", {})
        )
        shortcuts_layout.addWidget(self.shortcut_widgets["MODE_TOGGLE"])

        # Show/hide window
        self.shortcut_widgets["WINDOW_TOGGLE"] = self.create_shortcut_config(
            "Show/hide window", self.shortcuts_config.get("WINDOW_TOGGLE", {})
        )
        shortcuts_layout.addWidget(self.shortcut_widgets["WINDOW_TOGGLE"])

        shortcuts_group.setLayout(shortcuts_layout)
        layout.addWidget(shortcuts_group)

        # Button area
        btn_layout = QHBoxLayout()
        self.reset_btn = QPushButton("Restore Defaults")
        self.reset_btn.clicked.connect(self.reset_to_defaults)
        btn_layout.addWidget(self.reset_btn)

        self.apply_btn = QPushButton("Apply")
        self.apply_btn.clicked.connect(self.apply_settings)
        btn_layout.addWidget(self.apply_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def create_shortcut_config(self, title, config):
        """
        Create a single shortcut configuration widget.
        """
        widget = QWidget()
        layout = QHBoxLayout()

        # Title
        layout.addWidget(QLabel(f"{title}:"))

        # Modifier key selection
        modifier_combo = QComboBox()
        modifier_combo.addItems(["Ctrl", "Alt", "Shift"])
        current_modifier = config.get("modifier", "ctrl").title()
        modifier_combo.setCurrentText(current_modifier)
        modifier_combo.currentTextChanged.connect(self.on_settings_changed)
        layout.addWidget(modifier_combo)

        # Key selection
        key_combo = QComboBox()
        key_combo.addItems([chr(i) for i in range(ord("a"), ord("z") + 1)])  # a-z
        current_key = config.get("key", "j").lower()
        key_combo.setCurrentText(current_key)
        key_combo.currentTextChanged.connect(self.on_settings_changed)
        layout.addWidget(key_combo)

        widget.setLayout(layout)
        widget.modifier_combo = modifier_combo
        widget.key_combo = key_combo
        return widget

    def on_settings_changed(self):
        """
        Settings changed callback.
        """
        self.settings_changed.emit()

    def apply_settings(self):
        """
        Apply settings.
        """
        try:
            # Update enabled state
            self.config.update_config(
                "SHORTCUTS.ENABLED", self.enable_checkbox.isChecked()
            )

            # Update individual shortcut configurations
            for key, widget in self.shortcut_widgets.items():
                modifier = widget.modifier_combo.currentText().lower()
                key_value = widget.key_combo.currentText().lower()

                self.config.update_config(f"SHORTCUTS.{key}.modifier", modifier)
                self.config.update_config(f"SHORTCUTS.{key}.key", key_value)

            # Reload configuration
            self.config.reload_config()
            self.shortcuts_config = self.config.get_config("SHORTCUTS", {})

            logger.info("Shortcut settings saved")

        except Exception as e:
            logger.error(f"Failed to save shortcut settings: {e}")

    def reset_to_defaults(self):
        """
        Restore default settings.
        """
        # Default configuration
        defaults = {
            "ENABLED": True,
            "MANUAL_PRESS": {"modifier": "ctrl", "key": "j"},
            "AUTO_TOGGLE": {"modifier": "ctrl", "key": "k"},
            "ABORT": {"modifier": "ctrl", "key": "q"},
            "MODE_TOGGLE": {"modifier": "ctrl", "key": "m"},
            "WINDOW_TOGGLE": {"modifier": "ctrl", "key": "w"},
        }

        # Update UI
        self.enable_checkbox.setChecked(defaults["ENABLED"])

        for key, config in defaults.items():
            if key == "ENABLED":
                continue

            widget = self.shortcut_widgets.get(key)
            if widget:
                widget.modifier_combo.setCurrentText(config["modifier"].title())
                widget.key_combo.setCurrentText(config["key"].lower())

        # Trigger change signal
        self.on_settings_changed()
