from pathlib import Path

from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTextEdit,
)

from src.utils.config_manager import ConfigManager
from src.utils.logging_config import get_logger
from src.utils.resource_finder import resource_finder
from src.views.settings.components.shortcuts_settings import ShortcutsSettingsWidget


class SettingsWindow(QDialog):
    """
    Parameter Configuration Window.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = get_logger(__name__)
        self.config_manager = ConfigManager.get_instance()

        # UI Controls
        self.ui_controls = {}

        # Shortcut Settings Component
        self.shortcuts_tab = None

        # Initialize UI
        self._setup_ui()
        self._connect_events()
        self._load_config_values()

    def _setup_ui(self):
        """
        Set up UI.
        """
        try:
            from PyQt5 import uic

            ui_path = Path(__file__).parent / "settings_window.ui"
            uic.loadUi(str(ui_path), self)

            # Get references to all UI controls
            self._get_ui_controls()

            # Add shortcut settings tab
            self._add_shortcuts_tab()

        except Exception as e:
            self.logger.error(f"Failed to set up UI: {e}", exc_info=True)
            raise

    def _add_shortcuts_tab(self):
        """
        Add shortcut settings tab.
        """
        try:
            # Get TabWidget
            tab_widget = self.findChild(QTabWidget, "tabWidget")
            if not tab_widget:
                self.logger.error("TabWidget control not found")
                return

            # Create shortcut settings component
            self.shortcuts_tab = ShortcutsSettingsWidget()

            # Add to tab
            tab_widget.addTab(self.shortcuts_tab, "Shortcuts")

            # Connect signals
            self.shortcuts_tab.settings_changed.connect(self._on_settings_changed)

            self.logger.debug("Successfully added shortcut settings tab")

        except Exception as e:
            self.logger.error(f"Failed to add shortcut settings tab: {e}", exc_info=True)

    def _on_settings_changed(self):
        """
        Settings change callback.
        """
        # You can add some tips or other logic here

    def _get_ui_controls(self):
        """
        Get UI control references.
        """
        # System option controls
        self.ui_controls.update(
            {
                "client_id_edit": self.findChild(QLineEdit, "client_id_edit"),
                "device_id_edit": self.findChild(QLineEdit, "device_id_edit"),
                "ota_url_edit": self.findChild(QLineEdit, "ota_url_edit"),
                "websocket_url_edit": self.findChild(QLineEdit, "websocket_url_edit"),
                "websocket_token_edit": self.findChild(
                    QLineEdit, "websocket_token_edit"
                ),
                "authorization_url_edit": self.findChild(
                    QLineEdit, "authorization_url_edit"
                ),
                "activation_version_combo": self.findChild(
                    QComboBox, "activation_version_combo"
                ),
            }
        )

        # MQTT configuration controls
        self.ui_controls.update(
            {
                "mqtt_endpoint_edit": self.findChild(QLineEdit, "mqtt_endpoint_edit"),
                "mqtt_client_id_edit": self.findChild(QLineEdit, "mqtt_client_id_edit"),
                "mqtt_username_edit": self.findChild(QLineEdit, "mqtt_username_edit"),
                "mqtt_password_edit": self.findChild(QLineEdit, "mqtt_password_edit"),
                "mqtt_publish_topic_edit": self.findChild(
                    QLineEdit, "mqtt_publish_topic_edit"
                ),
                "mqtt_subscribe_topic_edit": self.findChild(
                    QLineEdit, "mqtt_subscribe_topic_edit"
                ),
            }
        )

        # Wake word configuration controls
        self.ui_controls.update(
            {
                "use_wake_word_check": self.findChild(QCheckBox, "use_wake_word_check"),
                "model_path_edit": self.findChild(QLineEdit, "model_path_edit"),
                "model_path_btn": self.findChild(QPushButton, "model_path_btn"),
                "wake_words_edit": self.findChild(QTextEdit, "wake_words_edit"),
            }
        )

        # Camera configuration controls
        self.ui_controls.update(
            {
                "camera_index_spin": self.findChild(QSpinBox, "camera_index_spin"),
                "frame_width_spin": self.findChild(QSpinBox, "frame_width_spin"),
                "frame_height_spin": self.findChild(QSpinBox, "frame_height_spin"),
                "fps_spin": self.findChild(QSpinBox, "fps_spin"),
                "local_vl_url_edit": self.findChild(QLineEdit, "local_vl_url_edit"),
                "vl_api_key_edit": self.findChild(QLineEdit, "vl_api_key_edit"),
                "models_edit": self.findChild(QLineEdit, "models_edit"),
            }
        )

        # Button controls
        self.ui_controls.update(
            {
                "save_btn": self.findChild(QPushButton, "save_btn"),
                "cancel_btn": self.findChild(QPushButton, "cancel_btn"),
                "reset_btn": self.findChild(QPushButton, "reset_btn"),
            }
        )

    def _connect_events(self):
        """
        Connect event handlers.
        """
        if self.ui_controls["save_btn"]:
            self.ui_controls["save_btn"].clicked.connect(self._on_save_clicked)

        if self.ui_controls["cancel_btn"]:
            self.ui_controls["cancel_btn"].clicked.connect(self.reject)

        if self.ui_controls["reset_btn"]:
            self.ui_controls["reset_btn"].clicked.connect(self._on_reset_clicked)

        if self.ui_controls["model_path_btn"]:
            self.ui_controls["model_path_btn"].clicked.connect(
                self._on_model_path_browse
            )

    def _load_config_values(self):
        """
        Load values from configuration file to UI controls.
        """
        try:
            # System Options
            client_id = self.config_manager.get_config("SYSTEM_OPTIONS.CLIENT_ID", "")
            self._set_text_value("client_id_edit", client_id)

            device_id = self.config_manager.get_config("SYSTEM_OPTIONS.DEVICE_ID", "")
            self._set_text_value("device_id_edit", device_id)

            ota_url = self.config_manager.get_config(
                "SYSTEM_OPTIONS.NETWORK.OTA_VERSION_URL", ""
            )
            self._set_text_value("ota_url_edit", ota_url)

            websocket_url = self.config_manager.get_config(
                "SYSTEM_OPTIONS.NETWORK.WEBSOCKET_URL", ""
            )
            self._set_text_value("websocket_url_edit", websocket_url)

            websocket_token = self.config_manager.get_config(
                "SYSTEM_OPTIONS.NETWORK.WEBSOCKET_ACCESS_TOKEN", ""
            )
            self._set_text_value("websocket_token_edit", websocket_token)

            auth_url = self.config_manager.get_config(
                "SYSTEM_OPTIONS.NETWORK.AUTHORIZATION_URL", ""
            )
            self._set_text_value("authorization_url_edit", auth_url)

            # Activation Version
            activation_version = self.config_manager.get_config(
                "SYSTEM_OPTIONS.NETWORK.ACTIVATION_VERSION", "v1"
            )
            if self.ui_controls["activation_version_combo"]:
                combo = self.ui_controls["activation_version_combo"]
                combo.setCurrentText(activation_version)

            # MQTT Configuration
            mqtt_info = self.config_manager.get_config(
                "SYSTEM_OPTIONS.NETWORK.MQTT_INFO", {}
            )
            if mqtt_info:
                self._set_text_value(
                    "mqtt_endpoint_edit", mqtt_info.get("endpoint", "")
                )
                self._set_text_value(
                    "mqtt_client_id_edit", mqtt_info.get("client_id", "")
                )
                self._set_text_value(
                    "mqtt_username_edit", mqtt_info.get("username", "")
                )
                self._set_text_value(
                    "mqtt_password_edit", mqtt_info.get("password", "")
                )
                self._set_text_value(
                    "mqtt_publish_topic_edit", mqtt_info.get("publish_topic", "")
                )
                self._set_text_value(
                    "mqtt_subscribe_topic_edit", mqtt_info.get("subscribe_topic", "")
                )

            # Wake Word Configuration
            use_wake_word = self.config_manager.get_config(
                "WAKE_WORD_OPTIONS.USE_WAKE_WORD", False
            )
            if self.ui_controls["use_wake_word_check"]:
                self.ui_controls["use_wake_word_check"].setChecked(use_wake_word)

            self._set_text_value(
                "model_path_edit",
                self.config_manager.get_config("WAKE_WORD_OPTIONS.MODEL_PATH", ""),
            )

            # Wake Word List
            wake_words = self.config_manager.get_config(
                "WAKE_WORD_OPTIONS.WAKE_WORDS", []
            )
            wake_words_text = "\n".join(wake_words) if wake_words else ""
            if self.ui_controls["wake_words_edit"]:
                self.ui_controls["wake_words_edit"].setPlainText(wake_words_text)

            # Camera Configuration
            camera_config = self.config_manager.get_config("CAMERA", {})
            self._set_spin_value(
                "camera_index_spin", camera_config.get("camera_index", 0)
            )
            self._set_spin_value(
                "frame_width_spin", camera_config.get("frame_width", 640)
            )
            self._set_spin_value(
                "frame_height_spin", camera_config.get("frame_height", 480)
            )
            self._set_spin_value("fps_spin", camera_config.get("fps", 30))
            self._set_text_value(
                "local_vl_url_edit", camera_config.get("Local_VL_url", "")
            )
            self._set_text_value("vl_api_key_edit", camera_config.get("VLapi_key", ""))
            self._set_text_value("models_edit", camera_config.get("models", ""))

        except Exception as e:
            self.logger.error(f"Failed to load configuration values: {e}", exc_info=True)

    def _set_text_value(self, control_name: str, value: str):
        """
        Set the value of a text control.
        """
        control = self.ui_controls.get(control_name)
        if control and hasattr(control, "setText"):
            control.setText(str(value) if value is not None else "")

    def _set_spin_value(self, control_name: str, value: int):
        """
        Set the value of a numeric control.
        """
        control = self.ui_controls.get(control_name)
        if control and hasattr(control, "setValue"):
            control.setValue(int(value) if value is not None else 0)

    def _get_text_value(self, control_name: str) -> str:
        """
        Get the value of a text control.
        """
        control = self.ui_controls.get(control_name)
        if control and hasattr(control, "text"):
            return control.text().strip()
        return ""

    def _get_spin_value(self, control_name: str) -> int:
        """
        Get the value of a numeric control.
        """
        control = self.ui_controls.get(control_name)
        if control and hasattr(control, "value"):
            return control.value()
        return 0

    def _on_save_clicked(self):
        """
        Save button click event.
        """
        try:
            # Collect all configuration data
            success = self._save_all_config()

            if success:
                # Show save success and prompt for restart
                reply = QMessageBox.question(
                    self,
                    "Configuration Saved Successfully",
                    "Configuration saved successfully!\n\nTo make the configuration effective, it is recommended to restart the software.\nRestart now?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes,
                )

                if reply == QMessageBox.Yes:
                    self._restart_application()
                else:
                    self.accept()
            else:
                QMessageBox.warning(self, "Error", "Failed to save configuration, please check the input values.")

        except Exception as e:
            self.logger.error(f"Failed to save configuration: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"An error occurred while saving the configuration: {str(e)}")

    def _save_all_config(self) -> bool:
        """
        Save all configurations.
        """
        try:
            # System Options - Network Configuration
            ota_url = self._get_text_value("ota_url_edit")
            if ota_url:
                self.config_manager.update_config(
                    "SYSTEM_OPTIONS.NETWORK.OTA_VERSION_URL", ota_url
                )

            websocket_url = self._get_text_value("websocket_url_edit")
            if websocket_url:
                self.config_manager.update_config(
                    "SYSTEM_OPTIONS.NETWORK.WEBSOCKET_URL", websocket_url
                )

            websocket_token = self._get_text_value("websocket_token_edit")
            if websocket_token:
                self.config_manager.update_config(
                    "SYSTEM_OPTIONS.NETWORK.WEBSOCKET_ACCESS_TOKEN", websocket_token
                )

            authorization_url = self._get_text_value("authorization_url_edit")
            if authorization_url:
                self.config_manager.update_config(
                    "SYSTEM_OPTIONS.NETWORK.AUTHORIZATION_URL", authorization_url
                )

            # Activation Version
            if self.ui_controls["activation_version_combo"]:
                activation_version = self.ui_controls[
                    "activation_version_combo"
                ].currentText()
                self.config_manager.update_config(
                    "SYSTEM_OPTIONS.NETWORK.ACTIVATION_VERSION", activation_version
                )

            # MQTT Configuration
            mqtt_config = {}
            mqtt_endpoint = self._get_text_value("mqtt_endpoint_edit")
            if mqtt_endpoint:
                mqtt_config["endpoint"] = mqtt_endpoint

            mqtt_client_id = self._get_text_value("mqtt_client_id_edit")
            if mqtt_client_id:
                mqtt_config["client_id"] = mqtt_client_id

            mqtt_username = self._get_text_value("mqtt_username_edit")
            if mqtt_username:
                mqtt_config["username"] = mqtt_username

            mqtt_password = self._get_text_value("mqtt_password_edit")
            if mqtt_password:
                mqtt_config["password"] = mqtt_password

            mqtt_publish_topic = self._get_text_value("mqtt_publish_topic_edit")
            if mqtt_publish_topic:
                mqtt_config["publish_topic"] = mqtt_publish_topic

            mqtt_subscribe_topic = self._get_text_value("mqtt_subscribe_topic_edit")
            if mqtt_subscribe_topic:
                mqtt_config["subscribe_topic"] = mqtt_subscribe_topic

            if mqtt_config:
                # Get existing MQTT configuration and update
                existing_mqtt = self.config_manager.get_config(
                    "SYSTEM_OPTIONS.NETWORK.MQTT_INFO", {}
                )
                existing_mqtt.update(mqtt_config)
                self.config_manager.update_config(
                    "SYSTEM_OPTIONS.NETWORK.MQTT_INFO", existing_mqtt
                )

            # Wake Word Configuration
            if self.ui_controls["use_wake_word_check"]:
                use_wake_word = self.ui_controls["use_wake_word_check"].isChecked()
                self.config_manager.update_config(
                    "WAKE_WORD_OPTIONS.USE_WAKE_WORD", use_wake_word
                )

            model_path = self._get_text_value("model_path_edit")
            if model_path:
                self.config_manager.update_config(
                    "WAKE_WORD_OPTIONS.MODEL_PATH", model_path
                )

            # Wake Word List
            if self.ui_controls["wake_words_edit"]:
                wake_words_text = (
                    self.ui_controls["wake_words_edit"].toPlainText().strip()
                )
                wake_words = [
                    word.strip() for word in wake_words_text.split("\n") if word.strip()
                ]
                self.config_manager.update_config(
                    "WAKE_WORD_OPTIONS.WAKE_WORDS", wake_words
                )

            # Camera Configuration
            camera_config = {}
            camera_config["camera_index"] = self._get_spin_value("camera_index_spin")
            camera_config["frame_width"] = self._get_spin_value("frame_width_spin")
            camera_config["frame_height"] = self._get_spin_value("frame_height_spin")
            camera_config["fps"] = self._get_spin_value("fps_spin")

            local_vl_url = self._get_text_value("local_vl_url_edit")
            if local_vl_url:
                camera_config["Local_VL_url"] = local_vl_url

            vl_api_key = self._get_text_value("vl_api_key_edit")
            if vl_api_key:
                camera_config["VLapi_key"] = vl_api_key

            models = self._get_text_value("models_edit")
            if models:
                camera_config["models"] = models

            # Get existing camera configuration and update
            existing_camera = self.config_manager.get_config("CAMERA", {})
            existing_camera.update(camera_config)
            self.config_manager.update_config("CAMERA", existing_camera)

            self.logger.info("Configuration saved successfully")
            return True

        except Exception as e:
            self.logger.error(f"Error saving configuration: {e}", exc_info=True)
            return False

    def _on_reset_clicked(self):
        """
        Reset button click event.
        """
        reply = QMessageBox.question(
            self,
            "Confirm Reset",
            "Are you sure you want to reset all configurations to their default values?\nThis will clear all current settings.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            self._reset_to_defaults()

    def _reset_to_defaults(self):
        """
        Reset to default values.
        """
        try:
            # Get default configuration
            default_config = ConfigManager.DEFAULT_CONFIG

            # System Options
            self._set_text_value(
                "ota_url_edit",
                default_config["SYSTEM_OPTIONS"]["NETWORK"]["OTA_VERSION_URL"],
            )
            self._set_text_value("websocket_url_edit", "")
            self._set_text_value("websocket_token_edit", "")
            self._set_text_value(
                "authorization_url_edit",
                default_config["SYSTEM_OPTIONS"]["NETWORK"]["AUTHORIZATION_URL"],
            )

            if self.ui_controls["activation_version_combo"]:
                self.ui_controls["activation_version_combo"].setCurrentText(
                    default_config["SYSTEM_OPTIONS"]["NETWORK"]["ACTIVATION_VERSION"]
                )

            # Clear MQTT configuration
            self._set_text_value("mqtt_endpoint_edit", "")
            self._set_text_value("mqtt_client_id_edit", "")
            self._set_text_value("mqtt_username_edit", "")
            self._set_text_value("mqtt_password_edit", "")
            self._set_text_value("mqtt_publish_topic_edit", "")
            self._set_text_value("mqtt_subscribe_topic_edit", "")

            # Wake Word Configuration
            wake_word_config = default_config["WAKE_WORD_OPTIONS"]
            if self.ui_controls["use_wake_word_check"]:
                self.ui_controls["use_wake_word_check"].setChecked(
                    wake_word_config["USE_WAKE_WORD"]
                )

            self._set_text_value("model_path_edit", wake_word_config["MODEL_PATH"])

            if self.ui_controls["wake_words_edit"]:
                wake_words_text = "\n".join(wake_word_config["WAKE_WORDS"])
                self.ui_controls["wake_words_edit"].setPlainText(wake_words_text)

            # Camera Configuration
            camera_config = default_config["CAMERA"]
            self._set_spin_value("camera_index_spin", camera_config["camera_index"])
            self._set_spin_value("frame_width_spin", camera_config["frame_width"])
            self._set_spin_value("frame_height_spin", camera_config["frame_height"])
            self._set_spin_value("fps_spin", camera_config["fps"])
            self._set_text_value("local_vl_url_edit", camera_config["Local_VL_url"])
            self._set_text_value("vl_api_key_edit", camera_config["VLapi_key"])
            self._set_text_value("models_edit", camera_config["models"])

            self.logger.info("Configuration has been reset to default values")

        except Exception as e:
            self.logger.error(f"Failed to reset configuration: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"An error occurred while resetting the configuration: {str(e)}")

    def _on_model_path_browse(self):
        """
        Browse model path.
        """
        try:
            current_path = self._get_text_value("model_path_edit")
            if not current_path:
                # Use resource_finder to find the default models directory
                models_dir = resource_finder.find_models_dir()
                if models_dir:
                    current_path = str(models_dir)
                else:
                    # If not found, use models in the project root directory
                    project_root = resource_finder.get_project_root()
                    current_path = str(project_root / "models")

            selected_path = QFileDialog.getExistingDirectory(
                self, "Select Model Directory", current_path
            )

            if selected_path:
                self._set_text_value("model_path_edit", selected_path)
                self.logger.info(f"Selected model path: {selected_path}")

        except Exception as e:
            self.logger.error(f"Failed to browse model path: {e}", exc_info=True)
            QMessageBox.warning(self, "Error", f"An error occurred while browsing the model path: {str(e)}")

    def _restart_application(self):
        """
        Restart application.
        """
        try:
            self.logger.info("User chose to restart the application")

            # Close settings window
            self.accept()

            # Restart the program directly
            self._direct_restart()

        except Exception as e:
            self.logger.error(f"Restart application failed: {e}", exc_info=True)
            QMessageBox.warning(
                self, "Restart Failed", "Automatic restart failed, please restart the software manually for the configuration to take effect."
            )

    def _direct_restart(self):
        """
        Restart the program directly.
        """
        try:
            import os
            import sys

            # Get the current program path and parameters
            python = sys.executable
            script = sys.argv[0]
            args = sys.argv[1:]

            self.logger.info(f"Restart command: {python} {script} {' '.join(args)}")

            # Close current application
            from PyQt5.QtWidgets import QApplication

            QApplication.quit()

            # Start new instance
            if getattr(sys, "frozen", False):
                # Packaged environment
                os.execv(sys.executable, [sys.executable] + args)
            else:
                # Development environment
                os.execv(python, [python, script] + args)

        except Exception as e:
            self.logger.error(f"Direct restart failed: {e}", exc_info=True)

    def closeEvent(self, event):
        """
        Window close event.
        """
        self.logger.debug("Settings window closed")
        super().closeEvent(event)
