---
title: Old User Manual
description: Old user manual for the py-xiaozhi project, providing usage guidelines for earlier versions
outline: deep
---

# py-xiaozhi User Manual (Please read carefully)

![Image](https://github.com/user-attachments/assets/df8bd5d2-a8e6-4203-8084-46789fc8e9ad)
## Introduction to Use
- There are two voice modes: push-to-talk and automatic conversation. The button in the bottom right corner shows the current mode.
- Push-to-talk: Hold to speak, release to send.
- Automatic conversation: Click to start the conversation. When the interface shows "Listening," it's your turn to speak. It will send automatically after you finish.
- GUI mode:
  - F2 key: Hold to speak
  - F3 key: Interrupt conversation
- CLI mode:
  - F2 key: Press once to start automatic conversation
  - F3 key: Interrupt conversation
  
## Configuration Description

### Project Base Configuration

#### Configuration File Description
The project uses two configuration methods: an initial configuration template and a runtime configuration file.

1. **Initial Configuration Template**
   - Location: `/src/utils/config_manager.py`
   - Purpose: Provides a default configuration template. A configuration file is automatically generated on the first run.
   - Use Case: Modify this file on the first run or when you need to reset the configuration.

2. **Runtime Configuration File**
   - Location: `/config/config.json`
   - Purpose: Stores the configuration information for actual runtime.
   - Use Case: Modify this file for daily use.

#### Configuration Item Description
- Add configurations as needed and retrieve them through `config_manager`. Refer to `websocket` or `iot\things\temperature_sensor.py` for examples.
- For example, to get the "endpoint" of "MQTT_INFO", you can use `config.get_config("MQTT_INFO.endpoint")`.
```json
{
  "CLIENT_ID": "Automatically generated client ID",
  "DEVICE_ID": "Device MAC address",
  "NETWORK": {
    "OTA_VERSION_URL": "OTA update address",
    "WEBSOCKET_URL": "WebSocket server address",
    "WEBSOCKET_ACCESS_TOKEN": "Access token"
  },
  "MQTT_INFO": {
    "endpoint": "MQTT server address",
    "client_id": "MQTT client ID",
    "username": "MQTT username",
    "password": "MQTT password",
    "publish_topic": "Publish topic",
    "subscribe_topic": "Subscribe topic"
  },
  "USE_WAKE_WORD": false,          // Whether to enable voice wake-up
  "WAKE_WORDS": [                  // List of wake words
    "Xiaozhi",
    "Hello Xiaoming"
  ],
  "WAKE_WORD_MODEL_PATH": "./models/vosk-model-small-cn-0.22",  // Wake word model path
  "TEMPERATURE_SENSOR_MQTT_INFO": {
    "endpoint": "Your Mqtt address",
    "port": 1883,
    "username": "admin",
    "password": "dtwin@123",
    "publish_topic": "sensors/temperature/command",
    "subscribe_topic": "sensors/temperature/device_001/state"
  },
  "CAMERA": { // Vision configuration
    "camera_index": 0,
    "frame_width": 640,
    "frame_height": 480,
    "fps": 30,
    "Loacl_VL_url": "https://open.bigmodel.cn/api/paas/v4/", // Zhipu application address https://open.bigmodel.cn/
    "VLapi_key": "Your key"
  }
  // ...you can add any configuration
}
```

#### Configuration Modification Guide

1. **First-time Use Configuration**
   - Run the program directly, and the system will automatically generate a default configuration file.
   - If you need to modify the default values, you can edit `DEFAULT_CONFIG` in `config_manager.py`.

2. **Changing Server Configuration**
   - Open `/config/config.json`.
   - Modify `NETWORK.WEBSOCKET_URL` to the new server address.
   - Example:
     ```json
     "NETWORK": {
       "WEBSOCKET_URL": "ws://your_server_address:port/"
     }
     ```
   
3. **Enabling Voice Wake-up**
   - Change `USE_WAKE_WORD` to `true`.
   - You can add or modify wake words in the `WAKE_WORDS` array.

#### Notes
- You need to restart the program for configuration changes to take effect.
- The WebSocket URL must start with `ws://` or `wss://`.
- A `CLIENT_ID` is automatically generated on the first run. It is recommended not to modify it manually.
- `DEVICE_ID` defaults to the device's MAC address but can be modified as needed.
- The configuration file uses UTF-8 encoding. Please use a UTF-8 compatible editor to modify it.

## Startup Instructions
### System Dependency Installation
#### Windows
1. **Install FFmpeg**
   ```bash
   # Method 1: Use Scoop to install (recommended)
   scoop install ffmpeg
   
   # Method 2: Manual installation
   # 1. Visit https://github.com/BtbN/FFmpeg-Builds/releases to download
   # 2. Unzip and add the bin directory to the system PATH
   ```

2. **Opus Audio Codec Library**
   - The project automatically includes `opus.dll` by default, so no manual installation is required.
   - If you encounter problems, you can copy `/libs/windows/opus.dll` to one of the following locations:
     - The application directory
     - `C:\Windows\System32`

#### Linux (Debian/Ubuntu)
```bash
# Install system dependencies
sudo apt-get update
sudo apt-get install python3-pyaudio portaudio19-dev ffmpeg libopus0 libopus-dev

# Install volume control dependencies (choose one of the following three)
# 1. PulseAudio tools (recommended)
sudo apt-get install pulseaudio-utils

# 2. Or ALSA tools
sudo apt-get install alsa-utils

# 3. If you need to use the alsamixer method, you also need to install expect
sudo apt-get install alsa-utils expect


sudo apt install build-essential python3-dev
```

#### macOS
```bash
# Use Homebrew to install system dependencies
brew install portaudio opus python-tk ffmpeg gfortran
brew upgrade tcl-tk
```

### Python Dependency Installation

#### Method 1: Use venv (recommended)
```bash
# 1. Create a virtual environment
python -m venv .venv

# 2. Activate the virtual environment
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

# 3. Install dependencies
# Windows/Linux
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple
# macOS
pip install -r requirements_mac.txt -i https://mirrors.aliyun.com/pypi/simple
```

#### Method 2: Use Conda
```bash
# 1. Create a Conda environment
conda create -n py-xiaozhi python=3.12

# 2. Activate the environment
conda activate py-xiaozhi

# 3. Install Conda-specific dependencies
conda install conda-forge::libopus
conda install conda-forge::ffmpeg

# 4. Install Python dependencies
# Windows/Linux
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple
# macOS
pip install -r requirements_mac.txt -i https://mirrors.aliyun.com/pypi/simple
```

### Wake Word Model

- [Download Wake Word Model](https://alphacephei.com/vosk/models)
- After downloading, unzip and place it in the root directory `/models`.
- By default, it reads the `vosk-model-small-cn-0.22` small model.
- ![Image](../images/Wake_Word.png)

### IoT Function Description

#### IoT Module Structure

```
├── iot                          # IoT device related modules
│   ├── things                   # Directory for specific device implementations
│   │   ├── lamp.py              # Smart lamp control implementation
│   │   │   └── Lamp             # Lamp device class, provides functions like on/off, brightness adjustment, color change, etc.
│   │   ├── music_player.py      # Music player implementation
│   │   │   └── MusicPlayer      # Music player class, provides functions like play, pause, switch songs, etc.
│   │   └── speaker.py           # Volume control implementation
│   │       └── Speaker          # Speaker class, provides volume adjustment, mute, etc.
│   ├── thing.py                 # IoT device base class definition
│   │   ├── Thing                # Abstract base class for all IoT devices
│   │   ├── Property             # Device property class, defines the mutable state of the device
│   │   ├── Action               # Device action class, defines the executable operations of the device
│   │   └── Event                # Device event class, defines the events that the device can trigger
│   └── thing_manager.py         # IoT device manager (manages various devices uniformly)
│       └── ThingManager         # Singleton pattern implementation of the device manager, responsible for device registration, lookup, and command dispatch
```

#### IoT State Flow
```text
                                  +----------------+
                                  |    User Voice  |
                                  |    Command     |
                                  +-------+-------+
                                          |
                                          v
                                  +-------+-------+
                                  | Speech Recognition |
                                  |   (STT)      |
                                  +-------+-------+
                                          |
                                          v
                                  +-------+-------+
                                  |  LLM Process Command |
                                  |               |
                                  +-------+-------+
                                          |
                                          v
                                  +-------+-------+
                                  | Generate IoT Command |
                                  |               |
                                  +-------+-------+
                                          |
                                          v
                          +---------------+---------------+
                          |     Application Receives IoT Message    |
                          |    _handle_iot_message()     |
                          +---------------+---------------+
                                          |
                                          v
                          +---------------+---------------+
                          |    ThingManager.invoke()     |
                          +---------------+---------------+
                                          |
           +------------------+------------------+------------------+
           |                  |                  |                  |
           v                  v                  v                  v
+----------+-------+  +-------+--------+  +------+---------+  +----+-----------+
|     Lamp         |  |    Speaker     |  |   MusicPlayer  |  |    CameraVL    |
| (Control Lamp)   |  | (Control Volume)|  | (Play Music)   |  | (Camera & Vision) |
+----------+-------+  +-------+--------+  +------+---------+  +----+-----------+
           |                  |                  |                  |
           |                  |                  |                  |
           |                  |                  |                  v
           |                  |                  |           +------+---------+
           |                  |                  |           |   Camera.py    |
           |                  |                  |           | (Camera Control) |
           |                  |                  |           +------+---------+
           |                  |                  |                  |
           |                  |                  |                  v
           |                  |                  |           +------+---------+
           |                  |                  |           |     VL.py      |
           |                  |                  |           | (Vision Processing) |
           |                  |                  |           +------+---------+
           |                  |                  |                  |
           +------------------+------------------+------------------+
                                          |
                                          v
                          +---------------+---------------+
                          |        Execute Device Operation       |
                          +---------------+---------------+
                                          |
                                          v
                          +---------------+---------------+
                          |        Update Device Status         |
                          |    _update_iot_states()      |
                          +---------------+---------------+
                                          |
                                          v
                          +---------------+---------------+
                          |     Send Status Update to Server      |
                          |   send_iot_states(states)    |
                          +---------------+---------------+
                                          |
                                          v
                          +---------------+---------------+
                          |      Server Updates Device Status     |
                          +---------------+---------------+
                                          |
                                          v
                          +---------------+---------------+
                          |       Return Result to User        |
                          |      (Voice or UI Feedback)      |
                          +-------------------------------+
```

#### IoT Device Management
- The IoT module uses a flexible multi-protocol communication architecture:
  - MQTT protocol: Used for communication with standard IoT devices, such as smart lights, air conditioners, etc.
  - HTTP protocol: Used for interaction with web services, such as getting online music, calling multimodal AI models, etc.
  - Extensible to support other protocols: such as WebSocket, TCP, etc.
- Supports automatic discovery and management of IoT devices.
- IoT devices can be controlled by voice commands, for example:
  - "View current IoT devices"
  - "Turn on the living room light"
  - "Turn off the air conditioner"
  - "Set the temperature to 26 degrees"
  - "Turn on the camera"
  - "Turn off the camera"
  - "Recognize the screen"

#### Adding a New IoT Device
1. Create a new device class in the `src/iot/things` directory.
2. Inherit the `Thing` base class and implement the necessary methods.
3. Register the new device in `thing_manager.py`.

### Notes
1. Ensure that the corresponding server configurations are correct and accessible:
   - MQTT server configuration (for IoT devices)
   - API interface address (for HTTP services)
2. Devices/services of different protocols need to implement corresponding connection and communication logic.
3. It is recommended to add basic error handling and reconnection mechanisms for each new device/service.
4. You can support new communication protocols by extending the `Thing` base class.
5. When adding a new device, it is recommended to perform a communication test first to ensure a stable connection.

#### Online Music Configuration
- Online music source is connected, no need for self-configuration, available by default.
### Operating Mode Description
#### GUI Mode (Default)
```bash
python main.py
```


#### CLI Mode
```bash
python main.py --mode cli
```

#### Build and Package

Use PyInstaller to package into an executable file:

```bash
# Windows
python scripts/build.py

# macOS
python scripts/build.py

# Linux
python scripts/build.py
```

### Notes
1. It is recommended to use Python 3.9.13+ version, 3.12 is recommended.
2. Windows users do not need to manually install `opus.dll`, the project will handle it automatically.
3. When using a Conda environment, you must install `ffmpeg` and `Opus`.
4. When using a Conda environment, please do not share the same Conda environment with `esp32-server`, because the server's `websocket` dependency version is higher than this project's.
5. It is recommended to use a domestic mirror source to install dependencies, which can increase the download speed.
6. macOS users need to use the dedicated `requirements_mac.txt`.
7. Ensure that system dependencies are installed before installing Python dependencies.
8. If you use `xiaozhi-esp32-server` as the server, this project will only respond in automatic conversation mode.
9. esp32-server video deployment tutorial [New! Complete tutorial for local deployment of Xiaozhi AI server, supports DeepSeek access](https://www.bilibili.com/video/BV1GvQWYZEd2/?share_source=copy_web&vd_source=86370b0cff2da3ab6e3d26eb1cab13d3)
10. The volume control function requires specific dependencies to be installed. The program will automatically check and prompt for missing dependencies at startup.

### Volume Control Function Description

This application supports adjusting the system volume. Different operating systems require different dependencies to be installed:

1. **Windows**: Use `pycaw` and `comtypes` to control the system volume.
2. **macOS**: Use `applescript` to control the system volume.
3. **Linux**: Use `pactl` (PulseAudio), `wpctl` (PipeWire), `amixer` (ALSA), or `alsamixer` to control the volume according to the system environment.

The application will automatically check if these dependencies are installed at startup. If dependencies are missing, corresponding installation instructions will be displayed.

#### How to Use Volume Control

- **GUI mode**: Use the volume slider on the interface to adjust the volume.
- **CLI mode**: Use the `v <volume_value>` command to adjust the volume, for example, `v 50` sets the volume to 50%.

### State Flowchart

```
                        +----------------+
                        |                |
                        v                |
+------+  Wake word/Button  +------------+   |   +------------+
| IDLE | -----------> | CONNECTING | --+-> | LISTENING  |
+------+              +------------+       +------------+
   ^                                            |
   |                                            | Speech recognition complete
   |          +------------+                    v
   +--------- |  SPEAKING  | <-----------------+
     Playback complete +------------+
```

## Getting Help
If you encounter problems:

1. First, check the `docs/Exception_Summary.md` document.
2. Submit issues through GitHub Issues.
3. Seek help from the AI assistant.
4. Contact the author (WeChat is on the homepage) (Please prepare a Todesk link and state your purpose, the author will handle it on weekday evenings).