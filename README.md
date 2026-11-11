# ESP32 Wireless Lyrics Display

An ESP32 and SSD1306 OLED display that shows currently playing track information and timed lyrics received from a PC bridge over Wi-Fi. When no track is available, the display falls back to a 12-hour clock.

[![ESP32](https://img.shields.io/badge/Hardware-ESP32-00979D?logo=espressif&logoColor=white)](https://www.espressif.com/)
[![Arduino](https://img.shields.io/badge/Firmware-Arduino%20IDE-00979D?logo=arduino&logoColor=white)](https://www.arduino.cc/)
[![Python](https://img.shields.io/badge/Bridge-Python%203.8%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/API-Flask-000000?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)

## Features

- ESP32 firmware drives a 128×64 SSD1306 OLED over I²C.
- A PC-side Python bridge exposes track and lyric data over the local network.
- Supports Spotify/local playback detection paths and looks up timed lyrics through [LRCLIB](https://lrclib.net/).
- Falls back to a 12-hour clock when no track is playing.
- Includes a visual setup guide and launch scripts for Windows and macOS/Linux.

## How it works

1. The PC bridge checks for the current track and retrieves available lyric data.
2. Flask serves the current playback state as JSON at `/now-playing` on port `5000`.
3. The ESP32 requests that endpoint over the same Wi-Fi network.
4. The firmware parses the response and updates the OLED; when no playback data is available, it displays the clock.

The PC and ESP32 must be on the same reachable network. This is a hobby prototype; behaviour depends on the playback detection method, lyric availability, and local network configuration.

## Hardware

| Component | Requirement |
|---|---|
| Controller | ESP32 development board |
| Display | SSD1306 OLED, 128×64, I²C |
| OLED VCC | 3.3 V |
| OLED GND | GND |
| OLED SDA | GPIO 21 |
| OLED SCL | GPIO 22 |

Do not power a 3.3 V-only OLED module from 5 V. Check the markings and datasheet for your exact module before connecting it.

## Quick start

### 1. Prepare the ESP32 firmware

1. Install [Arduino IDE](https://www.arduino.cc/en/software) and ESP32 board support.
2. Install these libraries through Library Manager:
   - Adafruit SSD1306
   - Adafruit GFX Library
   - ArduinoJson
3. Open `esp32_firmware/esp32_lyrics_display/esp32_lyrics_display.ino`.
4. Set `WIFI_SSID`, `WIFI_PASSWORD`, and `PC_IP_ADDRESS` near the top of the sketch. Use the PC's local IPv4 address; keep `PC_PORT` set to `5000` unless you also change the bridge.
5. Select the correct ESP32 board and port, then compile and upload.

### 2. Start the PC bridge

**Windows**

Double-click `pc_bridge/start_bridge_windows.bat`. It installs the listed Python packages and starts the server.

**macOS/Linux**

Run from the repository root:

```bash
bash pc_bridge/start_bridge_mac_linux.sh
```

The launcher creates a local virtual environment, installs `pc_bridge/requirements.txt`, and starts the bridge.

### 3. Verify the bridge

On the PC, open [http://localhost:5000/now-playing](http://localhost:5000/now-playing). If the endpoint responds, power the ESP32 and check that its configured PC IP matches the PC's current local address.

## Repository structure

```text
.
├── esp32_firmware/
│   └── esp32_lyrics_display/
│       └── esp32_lyrics_display.ino  # Sketch folder and filename match Arduino IDE
├── pc_bridge/
│   ├── pc_bridge.py                  # Flask server and playback/lyrics logic
│   ├── requirements.txt              # Python dependencies
│   ├── start_bridge_windows.bat      # Windows launcher
│   └── start_bridge_mac_linux.sh     # macOS/Linux virtualenv launcher
├── docs/
│   └── visual_guide.html             # Visual setup guide
└── README.md
```

## Troubleshooting

| Symptom | Checks |
|---|---|
| OLED is blank | Verify 3.3 V/GND, SDA/SCL wiring, I²C address, and installed display libraries. |
| ESP32 cannot connect to Wi-Fi | Use a 2.4 GHz network and confirm the SSID/password. |
| Clock works but lyrics do not appear | Ensure the PC bridge is running, check `PC_IP_ADDRESS`, and confirm both devices can reach each other. |
| `/now-playing` does not load | Check the terminal for Python errors and ensure port 5000 is not blocked or already in use. |
| No lyrics for a track | The track may not have timed lyrics available from LRCLIB. |

## Skills demonstrated

- Embedded C++ and Arduino firmware
- ESP32 Wi-Fi networking and I²C peripherals
- Python, Flask, HTTP/JSON APIs
- Dependency management and cross-platform startup scripts
- Hardware integration and troubleshooting

## Limitations

- Track detection varies by operating system and player.
- Lyrics depend on external LRCLIB availability and matching metadata.
- The bridge listens on the local network. Do not expose it directly to the public internet without adding appropriate authentication and security controls.
- Optional playback API credentials may improve some integrations, but are not required for the basic OLED and bridge setup.

## Maintenance & validation

- **Documentation review:** 11 November 2026.
- **Scope:** README and repository layout were updated to match the actual files.
- **Runtime status:** The file move and documentation changes have not been followed by a hardware compile or end-to-end playback test in this session.
- **Before relying on it:** Install the bridge dependencies, start the local endpoint, compile/upload the ESP32 sketch, and verify Wi-Fi reachability and OLED output on the target hardware.
