/*
 * ESP32 OLED Lyrics Display
 * ========================
 * Shows song lyrics from Spotify/YouTube Music on a 0.96" OLED
 * Falls back to a 12-hour clock when nothing is playing
 *
 * Hardware:
 *   - ESP32 (any variant)
 *   - 0.96" SSD1306 OLED (128x64, I2C)
 *     SDA -> GPIO 21
 *     SCL -> GPIO 22
 *     VCC -> 3.3V
 *     GND -> GND
 *
 * Libraries needed (install via Arduino Library Manager):
 *   - Adafruit SSD1306
 *   - Adafruit GFX Library
 *   - ArduinoJson
 *   - WiFi (built-in for ESP32)
 */

#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <WiFi.h>
#include <WiFiClient.h>
#include <ArduinoJson.h>

// ──────────────────────────────────────────────
//  ★  CONFIGURE THESE SETTINGS  ★
// ──────────────────────────────────────────────
const char* WIFI_SSID     = "YOUR_WIFI_NAME";      // Your WiFi network name
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";  // Your WiFi password
const char* PC_IP_ADDRESS = "192.168.1.XXX";       // IP of your PC (see README)
const int   PC_PORT       = 5000;                  // Must match pc_bridge port
// ──────────────────────────────────────────────

#define SCREEN_WIDTH  128
#define SCREEN_HEIGHT  64
#define OLED_RESET     -1   // No reset pin needed
#define SCREEN_ADDRESS 0x3C // Most 0.96" OLEDs use 0x3C

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

// State
String currentSong   = "";
String currentArtist = "";
String currentLyric  = "";
bool   isPlaying     = false;

unsigned long lastFetch    = 0;
unsigned long lastScroll   = 0;
unsigned long lastClockDraw = 0;

const long FETCH_INTERVAL  = 2000;  // Fetch new data every 2 seconds
const long SCROLL_SPEED    = 60;    // Milliseconds between scroll steps
const long CLOCK_REFRESH   = 1000; // Clock update interval

int  scrollX        = 128;
int  lyricScrollX   = 128;
bool scrollingTitle = false;
bool scrollingLyric = false;

// ──────────────────────────────────────────────

void setup() {
  Serial.begin(115200);
  Serial.println("\n🎵 ESP32 Lyrics Display Booting...");

  // Init OLED
  if (!display.begin(SSD1306_SWITCHCAPVCC, SCREEN_ADDRESS)) {
    Serial.println("❌ SSD1306 not found! Check wiring.");
    while (true); // Halt
  }

  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);

  showBootScreen();

  // Connect to WiFi
  connectWiFi();

  Serial.println("✅ Ready!");
}

void loop() {
  unsigned long now = millis();

  // Fetch new data from PC every FETCH_INTERVAL ms
  if (now - lastFetch >= FETCH_INTERVAL) {
    lastFetch = now;
    fetchFromPC();
  }

  // Draw UI
  if (isPlaying) {
    drawNowPlaying(now);
  } else {
    drawClock(now);
  }
}

// ──────────────────────────────────────────────
//  NETWORKING
// ──────────────────────────────────────────────

void connectWiFi() {
  showMessage("Connecting to", WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n✅ WiFi connected: " + WiFi.localIP().toString());
    showMessage("WiFi OK!", WiFi.localIP().toString().c_str());
    delay(1000);
  } else {
    Serial.println("\n❌ WiFi failed. Check credentials.");
    showMessage("WiFi FAILED", "Check README");
    delay(3000);
  }
}

void fetchFromPC() {
  if (WiFi.status() != WL_CONNECTED) {
    connectWiFi();
    return;
  }

  WiFiClient client;
  if (!client.connect(PC_IP_ADDRESS, PC_PORT)) {
    // PC bridge not running or wrong IP — silently show clock
    isPlaying = false;
    return;
  }

  // Send HTTP GET
  client.print("GET /now-playing HTTP/1.1\r\n");
  client.print("Host: ");
  client.print(PC_IP_ADDRESS);
  client.print("\r\n");
  client.print("Connection: close\r\n\r\n");

  // Wait for response
  unsigned long timeout = millis();
  while (client.available() == 0) {
    if (millis() - timeout > 3000) {
      client.stop();
      return;
    }
  }

  // Skip HTTP headers
  String response = "";
  bool bodyStarted = false;
  while (client.available()) {
    String line = client.readStringUntil('\n');
    if (!bodyStarted && line == "\r") {
      bodyStarted = true;
      continue;
    }
    if (bodyStarted) {
      response += line;
    }
  }
  client.stop();

  // Parse JSON
  parseResponse(response);
}

void parseResponse(String json) {
  StaticJsonDocument<512> doc;
  DeserializationError err = deserializeJson(doc, json);

  if (err) {
    isPlaying = false;
    return;
  }

  bool playing = doc["playing"] | false;

  if (!playing) {
    isPlaying = false;
    return;
  }

  String newSong   = doc["song"]   | "";
  String newArtist = doc["artist"] | "";
  String newLyric  = doc["lyric"]  | "";

  // Reset scroll if song changed
  if (newSong != currentSong) {
    currentSong   = newSong;
    currentArtist = newArtist;
    scrollX = 128;
  }

  // Reset lyric scroll if lyric changed
  if (newLyric != currentLyric) {
    currentLyric = newLyric;
    lyricScrollX = 128;
  }

  isPlaying = true;
}

// ──────────────────────────────────────────────
//  DISPLAY: NOW PLAYING
// ──────────────────────────────────────────────

void drawNowPlaying(unsigned long now) {
  display.clearDisplay();

  // ── Top bar: music note + "NOW PLAYING"
  display.setTextSize(1);
  display.setCursor(0, 0);
  display.print((char)13); // music note character
  display.print(" NOW PLAYING");

  // ── Divider
  display.drawLine(0, 10, 127, 10, SSD1306_WHITE);

  // ── Song title (scrolling, size 1)
  display.setTextSize(1);
  int titleWidth = currentSong.length() * 6; // ~6px per char at size 1

  if (titleWidth > 128) {
    // Scrolling title
    if (now - lastScroll >= SCROLL_SPEED) {
      lastScroll = now;
      scrollX--;
      if (scrollX < -titleWidth) scrollX = 128;
    }
    display.setCursor(scrollX, 14);
  } else {
    display.setCursor(0, 14);
  }
  display.print(currentSong);

  // ── Artist (static, truncated)
  display.setTextSize(1);
  String artistDisplay = currentArtist;
  if (artistDisplay.length() > 21) artistDisplay = artistDisplay.substring(0, 18) + "...";
  display.setCursor(0, 25);
  display.print(artistDisplay);

  // ── Divider
  display.drawLine(0, 35, 127, 35, SSD1306_WHITE);

  // ── Lyric line (scrolling, size 1)
  display.setTextSize(1);
  int lyricWidth = currentLyric.length() * 6;

  if (lyricWidth > 128) {
    if (now - lastScroll >= SCROLL_SPEED) {
      lyricScrollX--;
      if (lyricScrollX < -lyricWidth) lyricScrollX = 128;
    }
    display.setCursor(lyricScrollX, 40);
  } else {
    display.setCursor(0, 40);
  }
  display.print(currentLyric);

  // ── Bottom: animated bars
  drawVisualizerBars(now);

  display.display();
}

void drawVisualizerBars(unsigned long now) {
  // Simple animated equalizer-style bars at the bottom
  int bars = 16;
  int barWidth = 6;
  int gap = 2;
  int maxHeight = 10;

  for (int i = 0; i < bars; i++) {
    int h = random(2, maxHeight); // animate pseudo-randomly
    int x = i * (barWidth + gap);
    int y = 63 - h;
    display.fillRect(x, y, barWidth, h, SSD1306_WHITE);
  }
}

// ──────────────────────────────────────────────
//  DISPLAY: CLOCK (fallback)
// ──────────────────────────────────────────────

void drawClock(unsigned long now) {
  // Only redraw every second
  if (now - lastClockDraw < CLOCK_REFRESH) return;
  lastClockDraw = now;

  display.clearDisplay();

  // ── "NO MUSIC" label
  display.setTextSize(1);
  display.setCursor(35, 0);
  display.print("NO MUSIC");

  // ── Decorative line
  display.drawLine(0, 10, 127, 10, SSD1306_WHITE);

  // ── Big clock (uptime-based, synced via PC bridge)
  // The PC bridge sends Unix timestamp in JSON; we compute time from it
  // For now we display uptime as HH:MM:SS until time sync arrives
  unsigned long secs  = now / 1000;
  unsigned long mins  = secs / 60;
  unsigned long hours = mins / 60;

  secs  %= 60;
  mins  %= 60;

  // 12-hour format
  int h12 = hours % 12;
  if (h12 == 0) h12 = 12;
  bool isPM = (hours % 24) >= 12;

  char timeStr[9];
  sprintf(timeStr, "%2d:%02lu:%02lu", h12, mins, secs);

  display.setTextSize(2);
  display.setCursor(10, 20);
  display.print(timeStr);

  display.setTextSize(1);
  display.setCursor(105, 20);
  display.print(isPM ? "PM" : "AM");

  // ── Decorative bottom line
  display.drawLine(0, 53, 127, 53, SSD1306_WHITE);

  display.setTextSize(1);
  display.setCursor(15, 56);
  display.print("play something :)");

  display.display();
}

// ──────────────────────────────────────────────
//  HELPERS
// ──────────────────────────────────────────────

void showBootScreen() {
  display.clearDisplay();
  display.setTextSize(1);
  display.setCursor(20, 10);
  display.print("LYRICS DISPLAY");
  display.setCursor(35, 22);
  display.print("v1.0  ESP32");
  display.drawRect(0, 0, 128, 64, SSD1306_WHITE);
  display.display();
  delay(2000);
}

void showMessage(const char* line1, const char* line2) {
  display.clearDisplay();
  display.setTextSize(1);
  display.setCursor(0, 20);
  display.println(line1);
  display.println(line2);
  display.display();
}
