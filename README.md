# 🎵 ESP32 Wireless Lyrics Display

Show **live song lyrics** from Spotify or YouTube Music on a tiny 0.96" OLED — completely wireless via WiFi. Falls back to a **12-hour clock** when nothing is playing.

> 👉 **New to this? Open [`docs/visual_guide.html`](docs/visual_guide.html) in your browser for a full visual step-by-step guide with diagrams!**

---

## ✨ Features

- 📡 **Wireless** — ESP32 fetches data over WiFi, no USB needed after setup
- 🎵 **Spotify & YouTube Music** — auto-detects what's playing
- 🎤 **Synced Lyrics** — shows the current lyric line in real time (via lrclib.net, free, no API key)
- 🕐 **12-Hour Clock** — beautiful fallback when no music is playing
- 🔄 **Scrolling text** — long song names and lyrics scroll automatically
- 📊 **Visualizer bars** — animated equalizer at the bottom while music plays

---

## 🛒 Parts List

| Part | Details | Approx Cost |
|------|---------|-------------|
| ESP32 Dev Board | Any variant (DevKit, NodeMCU-32S, etc.) | $4–8 |
| 0.96" OLED | SSD1306, 128×64, I2C (4-pin) | $2–5 |
| 4× Jumper Wires | Female-to-Female | $1 |

**Total: ~$7–14**

---

## 🔌 Wiring (Only 4 Wires!)

```
OLED Pin  →  ESP32 Pin
────────────────────────
VCC       →  3.3V   ⚠️ NOT 5V!
GND       →  GND
SDA       →  GPIO 21
SCL       →  GPIO 22
```

---

## 🚀 Quick Start

### Step 1 — Install Arduino IDE
Download from [arduino.cc](https://www.arduino.cc/en/software) and add ESP32 support via Boards Manager URL:
```
https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
```

### Step 2 — Install Arduino Libraries
In Arduino IDE → Tools → Manage Libraries, install:
- `Adafruit SSD1306`
- `Adafruit GFX Library`
- `ArduinoJson`

### Step 3 — Configure the ESP32 Firmware
Open `esp32_firmware/esp32_lyrics_display.ino` and edit these lines:
```cpp
const char* WIFI_SSID     = "YourWiFiName";
const char* WIFI_PASSWORD = "YourWiFiPassword";
const char* PC_IP_ADDRESS = "192.168.1.XXX";  // your PC's local IP
```

To find your PC's IP:
- **Windows:** run `ipconfig` in Command Prompt → look for "IPv4 Address"
- **Mac:** System Settings → WiFi → Details
- **Linux:** run `ip addr` or `ifconfig`

### Step 4 — Upload to ESP32
Connect via USB → select your board and port → click Upload.

> 💡 If upload fails, hold the **BOOT button** on the ESP32 while clicking Upload.

### Step 5 — Run the PC Bridge
Install Python from [python.org](https://python.org) (check "Add to PATH").

**Windows:** Double-click `pc_bridge/start_bridge_windows.bat`

**Mac/Linux:**
```bash
cd pc_bridge
pip3 install -r requirements.txt
python3 pc_bridge.py
```

Test it: open http://localhost:5000/now-playing in your browser.

### Step 6 — Power On & Enjoy!
Plug ESP32 into any USB power source. Play music on Spotify or YouTube Music and watch the lyrics appear!

---

## 🗂 File Structure

```
esp32-lyrics-display/
├── esp32_firmware/
│   └── esp32_lyrics_display.ino   ← Upload to ESP32
├── pc_bridge/
│   ├── pc_bridge.py               ← Run on your PC
│   ├── requirements.txt
│   ├── start_bridge_windows.bat   ← Windows launcher
│   └── start_bridge_mac_linux.sh  ← Mac/Linux launcher
└── docs/
    └── visual_guide.html          ← Full visual tutorial
```

---

## 🔧 Troubleshooting

| Problem | Fix |
|---------|-----|
| OLED shows nothing | Check wiring; try changing `SCREEN_ADDRESS` to `0x3D` |
| ESP32 won't connect to WiFi | Use 2.4GHz network (ESP32 doesn't support 5GHz) |
| Clock shows but no lyrics | Make sure PC bridge is running + PC_IP_ADDRESS is correct |
| Upload fails | Hold BOOT button during upload; try a different USB cable |
| Song detected but no lyrics | Some songs aren't in lrclib.net — try a popular song to test |

---

## ⚙️ Optional: Spotify API (for better sync)

Without the API, lyrics sync uses a simple time estimate. For precise sync, get free credentials at [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard) and add them to `pc_bridge.py`:

```python
SPOTIFY_CLIENT_ID     = "your_client_id_here"
SPOTIFY_CLIENT_SECRET = "your_client_secret_here"
```

---

## 📋 Requirements

- Python 3.8+
- ESP32 on same WiFi network as PC
- PC bridge must be running for lyrics to work

---

*Uses [lrclib.net](https://lrclib.net) for free synced lyrics — no account or API key needed.*
