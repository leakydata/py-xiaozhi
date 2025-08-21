# Voice Interaction Mode Description

![Image](./images/System_Interface.png)

## Project Overview

py-xiaozhi is an AI voice assistant client developed in Python, featuring a modern asynchronous architecture design that supports rich multimodal interaction functions. The system integrates advanced technologies such as speech recognition, natural language processing, visual recognition, and IoT device control to provide users with an intelligent interactive experience.

### Core Features
- **Multi-protocol Support**: Dual protocol communication via WebSocket/MQTT
- **MCP Tool Ecosystem**: Integrated with 10+ professional tool modules
- **IoT Device Integration**: Thing-based architecture for device management
- **Visual Recognition**: Multimodal understanding based on GLM-4V
- **Audio Processing**: Opus encoding + WebRTC enhancement
- **Global Shortcuts**: System-level interaction control

## Voice Interaction Modes

The system offers multiple voice interaction methods, supporting flexible interaction control and intelligent voice detection:

### 1. Manual Press Mode

- **How to use**: Recording is active while the shortcut key is held down, and automatically sent upon release
- **Default Shortcut**: `Ctrl+J` (can be modified in the configuration)
- **Applicable Scenarios**: Precise control of recording time, avoiding interference from environmental noise
- **Advantages**:
  - Prevents accidental recording triggers
  - Recording duration is fully controllable
  - Suitable for use in noisy environments

### 2. Turn-based Mode

- **How to use**: Press the shortcut key to start/click the manual dialogue mode in the bottom right corner of the GUI to switch to automatic dialogue
- **Default Shortcut**: `Ctrl+K` (can be modified in the configuration)
- **Applicable Scenarios**: Continuous conversation, long-term interaction
- **Intelligent Features**: Supports continuous multi-turn dialogue

### 3. Wake Word Mode

- **How to use**: Activate the system by speaking the preset wake word
- **Default Wake Words**: "Xiaozhi", "Xiaomei" (can be customized in the configuration)
- **Model Support**: Based on Vosk offline speech recognition
- **Configuration Requirements**: Requires downloading the corresponding speech recognition model

### Mode Switching and Configuration

```json
// Configure shortcuts in config/config.json
{
  "SHORTCUTS": {
    "ENABLED": true,
    "MANUAL_PRESS": {"modifier": "ctrl", "key": "j"},
    "AUTO_TOGGLE": {"modifier": "ctrl", "key": "k"},
    "MODE_TOGGLE": {"modifier": "ctrl", "key": "m"}
  }
}
```

- **Interface Display**: The current interaction mode is displayed in real-time in the bottom right corner of the GUI
- **Quick Switching**: Use `Ctrl+M` to quickly switch between different modes
- **Status Indication**: The color of the system tray icon reflects the current status

## Dialogue Control and System Status

### Intelligent Interruption Function

When the AI is replying by voice, the user can interrupt the dialogue at any time:

- **Shortcut Interruption**: `Ctrl+Q` - Immediately stops the current AI reply
- **GUI Operation**: Click the "Interrupt" button on the interface
- **Intelligent Detection**: The system automatically interrupts the reply when new voice input is detected

### System Status Management

The system uses an event-driven state machine architecture with the following operating states:

```
┌─────────────────────────────────────────────────────────┐
│                    System State Flowchart                 │
└─────────────────────────────────────────────────────────┘

     IDLE              CONNECTING           LISTENING
  ┌─────────┐    Wake word/Button   ┌─────────┐  Connection successful  ┌─────────┐
  │  Idle   │  ─────────────> │ Connecting │ ────────> │ Listening │
  │ Standby │                │  Server    │           │ Recording │
  └─────────┘                └─────────┘           └─────────┘
       ↑                           │                     │
       │                         Connection failed      │ Speech recognition
       │                           │                     │ complete/timeout
       │                           ↓                     │
       │                     ┌─────────┐                 │
       └──── Playback complete/interrupted ──── │ Replying  │ <──────────────┘
                             │  AI speaking │
                             └─────────┘
```

### Status Indicator Description

**System Tray Icon Color**:
- **Green**: System is running normally, in standby mode
- **Yellow**: Listening to user voice input
- **Blue**: AI is replying by voice
- **Red**: System error or connection anomaly
- **Gray**: Not connected to the server

## Shortcut System

The system provides rich support for global shortcuts. For detailed instructions, please refer to: [Shortcut Description](./Shortcut_Description.md)

### Common Shortcuts

| Shortcut | Function Description | Notes |
|--------|----------|------|
| `Ctrl+J` | Push-to-talk mode | Recording is active while held down, sent upon release |
| `Ctrl+K` | Automatic dialogue mode | Toggles automatic voice detection on/off |
| `Ctrl+Q` | Interrupt dialogue | Immediately stops the AI reply |
| `Ctrl+M` | Switch interaction mode | Toggles between manual/automatic modes |
| `Ctrl+W` | Show/hide window | Minimizes/restores the window |

## Intelligent Voice Command System

### Basic Interaction Commands
- **Greetings**: "Hello", "Who are you", "Good morning"
- **Polite Phrases**: "Thank you", "Goodbye", "Please help me"
- **Status Inquiry**: "How is the system status", "Is the connection normal"

### Visual Recognition Commands

Integrated with GLM-4V for multimodal understanding:

```bash
# Visual recognition analysis
"Recognize the screen"             # Analyze the current camera feed
"What's in front of the camera"    # Describe what is seen
"What is this"         # Object recognition
```

### MCP Tool Invocation Commands

Utilizes the rich MCP tool ecosystem:

```bash
# Calendar management
"Create a meeting reminder for 3 PM tomorrow"
"Check today's schedule"

# Timer function
"Play 'Chrysanthemum Terrace' in one minute"

# System operations
"View system information"
"Adjust volume to 80%"

# Web search
"Search for today's weather"
"Find recent hot topics"

# Map navigation
"Find nearby coffee shops"
"Navigate to Tiananmen Square in Beijing"

# Food recipes
"Recommend a dinner recipe for tonight"
"Teach me how to make Kung Pao Chicken"

# Bazi fortune-telling (optional)
"Analyze my birth chart"
"How is my fortune today"
```

## Operating Modes and Deployment

### GUI Mode (Default)

Graphical User Interface mode, providing an intuitive interactive experience:

```bash
# Standard startup
python main.py

# Use MQTT protocol
python main.py --protocol mqtt
```

**GUI Mode Features**:
- Visual operation interface
- Real-time status display
- Audio waveform visualization
- System tray support
- Graphical settings interface

### CLI Mode

Command-Line Interface mode, suitable for server deployment:

```bash
# CLI mode startup
python main.py --mode cli

# CLI + MQTT protocol
python main.py --mode cli --protocol mqtt
```

**CLI Mode Features**:
- Low resource consumption
- Server-friendly
- Detailed log output
- Keyboard shortcut support
- Scripted deployment

**Build Features**:
- Cross-platform support
- Single-file mode
- Dependency packaging
- Automated configuration

## Platform Compatibility

### Windows Platform
- **Fully Compatible**: All functions are supported normally
- **Audio Enhancement**: Supports Windows Audio API
- **Volume Control**: Integrated with pycaw for volume management
- **System Tray**: Full tray functionality support
- **Global Hotkeys**: Full shortcut functionality

### macOS Platform
- **Fully Compatible**: Core functions are fully supported
- **Status Bar**: Tray icon is displayed in the top status bar
- **Permission Management**: May require authorization for microphone/camera access
- **Shortcuts**: Some shortcuts require system permissions
- **Audio**: Native CoreAudio support

### Linux Platform
- **Compatibility**: Supports mainstream distributions (Ubuntu/CentOS/Debian)
- **Desktop Environment**:
  - GNOME: Full support
  - KDE: Full support
  - Xfce: Requires additional tray support
- **Audio System**:
  - PulseAudio: Recommended (auto-detected)
  - ALSA: Fallback option
- **Dependencies**: May require installation of system tray support packages

```bash
# Ubuntu/Debian tray support
sudo apt-get install libappindicator3-1

# CentOS/RHEL tray support
sudo yum install libappindicator-gtk3
```

## Troubleshooting Guide

### Common Issues

**1. Speech recognition not working**
- Use simple wake words for recognition like "Xiaomei", "Xiaoming"

**2. Camera not working**
```bash
# Test the camera
python scripts/camera_scanner.py

# Check camera permissions and device index
```

**3. Shortcuts not responding**
- Check if other programs are using the same shortcuts
- Try running with administrator privileges (Windows)
- Check for interference from system security software

**4. Network connection issues**
- Check firewall settings
- Verify WebSocket/MQTT server address
- Test network connectivity
```