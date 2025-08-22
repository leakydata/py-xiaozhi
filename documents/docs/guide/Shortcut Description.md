# Shortcut Description

## Overview

py-xiaozhi provides full support for global shortcuts, allowing for quick operations even when running in the background. The shortcut system is implemented based on the pynput library and supports cross-platform use.

## Default Shortcuts

| Category | Shortcut | Function Description | Usage Scenario |
|---------|-------|---------|----------|
| **Voice Interaction** | `Ctrl+J` | Push-to-talk mode | Record while holding, send upon release |
| | `Ctrl+K` | Automatic dialogue mode | Toggle automatic voice detection on/off |
| | `Ctrl+Q` | Interrupt dialogue | Immediately stop AI reply |
| **Mode Control** | `Ctrl+M` | Switch interaction mode | Toggle between manual/automatic modes |
| | `Ctrl+W` | Show/hide window | Minimize/restore window |

## Detailed Shortcut Description

### Voice Interaction Shortcuts

#### Ctrl+J - Push to talk
- **Function**: Manual press mode, record while holding
- **How to use**:
  1. Hold down `Ctrl+J`
  2. Speak into the microphone
  3. Release the key to automatically send the voice
- **Applicable Scenarios**: Precise control of recording time, avoiding interference from environmental noise

#### Ctrl+K - Automatic dialogue
- **Function**: Toggle automatic dialogue mode on/off
- **How to use**: Press `Ctrl+K` to switch the automatic dialogue state
- **Applicable Scenarios**: Continuous conversation, long-term interaction

#### Ctrl+Q - Interrupt dialogue
- **Function**: Immediately stop the current AI voice reply
- **How to use**: Press `Ctrl+Q` during the AI reply
- **Applicable Scenarios**: When you need to urgently interrupt the AI reply

### Mode Control Shortcuts

#### Ctrl+M - Switch interaction mode
- **Function**: Switch between different voice interaction modes
- **How to use**: Press `Ctrl+M` to cycle through the modes
- **Mode Types**: Manual press mode ↔ Automatic dialogue mode

#### Ctrl+W - Show/hide window
- **Function**: Control the display state of the main window
- **How to use**: Press `Ctrl+W` to toggle window visibility
- **Applicable Scenarios**: Quickly hide/show the main interface

## Shortcut Configuration

### Configuration File Location

Shortcut configurations are stored in the `config/config.json` file:

```json
{
  "SHORTCUTS": {
    "ENABLED": true,
    "MANUAL_PRESS": {
      "modifier": "ctrl",
      "key": "j",
      "description": "Push to talk"
    },
    "AUTO_TOGGLE": {
      "modifier": "ctrl",
      "key": "k",
      "description": "Automatic dialogue"
    },
    "ABORT": {
      "modifier": "ctrl",
      "key": "q",
      "description": "Interrupt dialogue"
    },
    "MODE_TOGGLE": {
      "modifier": "ctrl",
      "key": "m",
      "description": "Switch mode"
    },
    "WINDOW_TOGGLE": {
      "modifier": "ctrl",
      "key": "w",
      "description": "Show/hide window"
    }
  }
}
```

### Customizing Shortcuts

#### Supported Modifier Keys

- `ctrl` - Ctrl key
- `alt` - Alt key
- `shift` - Shift key
- `ctrl+alt` - Ctrl+Alt combination
- `ctrl+shift` - Ctrl+Shift combination

#### Supported Main Keys

- **Letter keys**: a-z
- **Number keys**: 0-9
- **Function keys**: f1-f12
- **Special keys**: space, enter, tab, esc

#### Configuration Example

```json
{
  "SHORTCUTS": {
    "ENABLED": true,
    "MANUAL_PRESS": {
      "modifier": "alt",
      "key": "space",
      "description": "Push to talk"
    },
    "AUTO_TOGGLE": {
      "modifier": "ctrl+shift",
      "key": "a",
      "description": "Automatic dialogue"
    }
  }
}
```

## Platform Compatibility

### Windows
- **Full support**: All shortcut functions work normally
- **Permission requirements**: May require administrator privileges in some cases
- **Notes**: Avoid conflicts with system shortcuts

### macOS
- **Permission configuration**: Requires granting accessibility permissions
- **Configuration path**: System Preferences → Security & Privacy → Privacy → Accessibility
- **Terminal permissions**: If running from the terminal, the terminal needs to be granted permissions

### Linux
- **User group**: The user needs to be added to the `input` group
- **Configuration command**: `sudo usermod -a -G input $USER`
- **Desktop environment**: Supports X11 and Wayland

## Troubleshooting

### Shortcuts not responding

#### Check configuration
1. Confirm that `SHORTCUTS.ENABLED` is `true` in the configuration file
2. Check if the shortcut configuration format is correct
3. Verify the validity of the modifier and main keys

#### Permission issues
```bash
# macOS: Check accessibility permissions
System Preferences → Security & Privacy → Privacy → Accessibility

# Linux: Add user to audio group
sudo usermod -a -G input $USER

# Windows: Run as administrator
Right-click the application → Run as administrator
```

#### Conflict detection
1. Check if other programs are using the same shortcuts
2. Try changing to a less common shortcut combination
3. Close applications that may be causing conflicts

### Common Error Handling

#### ImportError: No module named 'pynput'
```bash
# Install the pynput library
pip install pynput
```

#### macOS permission denied
```bash
# Check and re-grant permissions
System Preferences → Security & Privacy → Privacy → Accessibility
# Remove and re-add the application
```

#### Linux keyboard listening failed
```bash
# Log out and log back in for the user group change to take effect
sudo usermod -a -G input $USER
# Log out and log back in
```

## Advanced Configuration

### Error Recovery Mechanism

The system has a built-in shortcut error recovery function:

- **Health check**: Checks the listener status every 30 seconds
- **Automatic restart**: Automatically restarts when a failure is detected
- **Error count**: Triggers recovery when the consecutive error limit is exceeded
- **State cleanup**: Cleans up the key state upon restart

### Debug Mode

Enable detailed log output:

```python
# Enable debug logging in the configuration
import logging
logging.getLogger('pynput').setLevel(logging.DEBUG)
```

### Performance Optimization

- **Key caching**: Reduces repeated key detection
- **Asynchronous processing**: Non-blocking key event handling
- **Resource management**: Automatic cleanup of listener resources

## Code Reference

Shortcut system implementation location:

- **Main implementation**: `src/views/components/shortcut_manager.py`
- **Configuration management**: `src/utils/config_manager.py`
- **Application integration**: `src/application.py`

### Core Methods

```python
# Start shortcut listening
from src.views.components.shortcut_manager import start_global_shortcuts_async
shortcut_manager = await start_global_shortcuts_async()

# Manually stop listening
await shortcut_manager.stop()
```