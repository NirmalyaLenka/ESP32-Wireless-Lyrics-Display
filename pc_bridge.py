"""
PC Bridge — Lyrics Display Server
===================================
Runs on your Windows/Mac/Linux PC and:
  1. Detects what's playing in Spotify or YouTube Music (browser tab)
  2. Fetches the current lyric line via lrclib.net (free, no API key!)
  3. Serves the data as JSON on http://0.0.0.0:5000/now-playing
     so your ESP32 can fetch it over WiFi

Requirements (install with: pip install -r requirements.txt):
  - flask
  - spotipy  (for Spotify)
  - requests
  - psutil
  - pywin32  (Windows only, for YouTube Music browser detection)

Usage:
  python pc_bridge.py

Then visit http://localhost:5000/now-playing in your browser to test it.
"""

import time
import threading
import requests
from flask import Flask, jsonify

# ──────────────────────────────────────────────
#  ★  OPTIONAL: SPOTIFY API CREDENTIALS  ★
#  Get free credentials at https://developer.spotify.com/dashboard
#  Leave blank to use Spotify local detection only (less reliable)
# ──────────────────────────────────────────────
SPOTIFY_CLIENT_ID     = ""   # e.g. "abc123..."
SPOTIFY_CLIENT_SECRET = ""   # e.g. "xyz789..."
SPOTIFY_REDIRECT_URI  = "http://localhost:8888/callback"
# ──────────────────────────────────────────────

app = Flask(__name__)

# Shared state (updated by background thread)
state = {
    "playing": False,
    "song": "",
    "artist": "",
    "lyric": "",
    "progress_ms": 0,
    "duration_ms": 0,
    "source": "none",   # "spotify" or "youtube_music"
}

# Cache lyrics so we don't spam the API
lyrics_cache = {
    "key": "",          # "artist|song"
    "lines": [],        # list of {"time": float, "text": str}
}


# ─────────────────────────────────────────────
#  SPOTIFY DETECTION
# ─────────────────────────────────────────────

def get_spotify_local():
    """
    Read the Spotify window title on Windows to get the current track.
    Returns (song, artist) or (None, None).
    Works even without API keys.
    """
    try:
        import psutil
        import subprocess
        import sys

        if sys.platform == "win32":
            # On Windows, Spotify sets the window title to "Artist - Song"
            import ctypes
            import ctypes.wintypes

            user32 = ctypes.windll.user32
            EnumWindows = user32.EnumWindows
            GetWindowText = user32.GetWindowTextW
            GetWindowTextLength = user32.GetWindowTextLengthW
            IsWindowVisible = user32.IsWindowVisible

            titles = []

            def callback(hwnd, _):
                if IsWindowVisible(hwnd):
                    length = GetWindowTextLength(hwnd)
                    if length > 0:
                        buf = ctypes.create_unicode_buffer(length + 1)
                        GetWindowText(hwnd, buf, length + 1)
                        titles.append(buf.value)
                return True

            WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
            EnumWindows(WNDENUMPROC(callback), 0)

            for title in titles:
                # Spotify sets title like "Song Name - Artist Name"
                # or just "Spotify" when paused
                if " - " in title and "Spotify" not in title:
                    parts = title.split(" - ", 1)
                    if len(parts) == 2:
                        return parts[0].strip(), parts[1].strip()

        elif sys.platform == "darwin":
            # macOS: use AppleScript
            script = '''
                tell application "Spotify"
                    if player state is playing then
                        return (name of current track) & "|" & (artist of current track)
                    end if
                end tell
            '''
            result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
            if result.returncode == 0 and "|" in result.stdout:
                parts = result.stdout.strip().split("|")
                return parts[0], parts[1]

        elif sys.platform.startswith("linux"):
            # Linux: use DBUS
            result = subprocess.run(
                ["dbus-send", "--print-reply", "--dest=org.mpris.MediaPlayer2.spotify",
                 "/org/mpris/MediaPlayer2", "org.freedesktop.DBus.Properties.Get",
                 "string:org.mpris.MediaPlayer2.Player", "string:Metadata"],
                capture_output=True, text=True
            )
            if "xesam:title" in result.stdout:
                lines = result.stdout.split("\n")
                song = artist = ""
                for i, line in enumerate(lines):
                    if "xesam:title" in line and i+1 < len(lines):
                        song = lines[i+1].strip().strip('"').strip("string ")
                    if "xesam:artist" in line and i+2 < len(lines):
                        artist = lines[i+2].strip().strip('"').strip("string ")
                if song:
                    return song, artist

    except Exception as e:
        print(f"[Spotify Local] {e}")

    return None, None


def get_spotify_api():
    """
    Use the Spotify Web API for richer data (progress, etc.)
    Only works if you've set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET.
    """
    if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
        return None

    try:
        import spotipy
        from spotipy.oauth2 import SpotifyOAuth

        sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=SPOTIFY_CLIENT_ID,
            client_secret=SPOTIFY_CLIENT_SECRET,
            redirect_uri=SPOTIFY_REDIRECT_URI,
            scope="user-read-playback-state",
            open_browser=True,
            cache_path=".spotify_cache"
        ))

        current = sp.current_playback()
        if current and current["is_playing"]:
            item = current["item"]
            return {
                "song": item["name"],
                "artist": item["artists"][0]["name"],
                "progress_ms": current["progress_ms"],
                "duration_ms": item["duration_ms"],
            }
    except Exception as e:
        print(f"[Spotify API] {e}")

    return None


# ─────────────────────────────────────────────
#  YOUTUBE MUSIC DETECTION (browser tab)
# ─────────────────────────────────────────────

def get_youtube_music():
    """
    Read the browser window title to detect YouTube Music.
    Chrome/Edge set the title to "Song - Artist - YouTube Music"
    """
    try:
        import sys
        import subprocess
        import ctypes
        import ctypes.wintypes

        if sys.platform == "win32":
            user32 = ctypes.windll.user32
            GetWindowText = user32.GetWindowTextW
            GetWindowTextLength = user32.GetWindowTextLengthW
            IsWindowVisible = user32.IsWindowVisible

            titles = []

            def callback(hwnd, _):
                if IsWindowVisible(hwnd):
                    length = GetWindowTextLength(hwnd)
                    if length > 0:
                        buf = ctypes.create_unicode_buffer(length + 1)
                        GetWindowText(hwnd, buf, length + 1)
                        titles.append(buf.value)
                return True

            WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
            user32.EnumWindows(WNDENUMPROC(callback), 0)

            for title in titles:
                # YouTube Music tab: "Song Name - Artist - YouTube Music"
                if "YouTube Music" in title and " - " in title:
                    parts = title.replace(" - YouTube Music", "").split(" - ")
                    if len(parts) >= 2:
                        return parts[0].strip(), parts[1].strip()

        elif sys.platform == "darwin":
            browsers = ["Google Chrome", "Firefox", "Safari", "Microsoft Edge"]
            for browser in browsers:
                script = f'''
                    tell application "{browser}"
                        set t to title of active tab of front window
                        return t
                    end tell
                '''
                result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
                title = result.stdout.strip()
                if "YouTube Music" in title and " - " in title:
                    parts = title.replace(" - YouTube Music", "").split(" - ")
                    if len(parts) >= 2:
                        return parts[0].strip(), parts[1].strip()

    except Exception as e:
        print(f"[YouTube Music] {e}")

    return None, None


# ─────────────────────────────────────────────
#  LYRICS FETCHING (lrclib.net — FREE, no key)
# ─────────────────────────────────────────────

def fetch_lyrics(song, artist):
    """
    Fetch synced (LRC) lyrics from lrclib.net.
    Returns list of {"time": float, "text": str} sorted by time.
    Falls back to unsynced lyrics if synced not available.
    """
    cache_key = f"{artist}|{song}".lower()

    if lyrics_cache["key"] == cache_key:
        return lyrics_cache["lines"]

    print(f"[Lyrics] Fetching: {song} by {artist}")

    lines = []
    try:
        # Try synced lyrics first
        resp = requests.get(
            "https://lrclib.net/api/get",
            params={"track_name": song, "artist_name": artist},
            timeout=5
        )

        if resp.status_code == 200:
            data = resp.json()
            synced_lyrics = data.get("syncedLyrics") or ""
            plain_lyrics = data.get("plainLyrics") or ""

            if synced_lyrics:
                # Parse LRC format: [mm:ss.xx] lyric line
                import re
                for match in re.finditer(r'\[(\d+):(\d+\.\d+)\](.*)', synced_lyrics):
                    minutes = int(match.group(1))
                    seconds = float(match.group(2))
                    text = match.group(3).strip()
                    if text:
                        lines.append({
                            "time": minutes * 60 + seconds,
                            "text": text
                        })
                print(f"[Lyrics] Got {len(lines)} synced lines")

            elif plain_lyrics:
                # No timestamps — just show lines sequentially every ~3 seconds
                raw_lines = [l.strip() for l in plain_lyrics.split("\n") if l.strip()]
                for i, text in enumerate(raw_lines):
                    lines.append({
                        "time": i * 3.0,
                        "text": text
                    })
                print(f"[Lyrics] Got {len(lines)} plain lines (no sync)")

    except Exception as e:
        print(f"[Lyrics] Error: {e}")

    # Cache result
    lyrics_cache["key"] = cache_key
    lyrics_cache["lines"] = lines

    return lines


def get_current_lyric(progress_ms, lines):
    """
    Given the current playback position, find the matching lyric line.
    """
    if not lines:
        return "♪ ♪ ♪"

    progress_sec = progress_ms / 1000.0
    current = lines[0]["text"]

    for line in lines:
        if line["time"] <= progress_sec:
            current = line["text"]
        else:
            break

    return current


# ─────────────────────────────────────────────
#  BACKGROUND POLLING THREAD
# ─────────────────────────────────────────────

def poll_loop():
    """Continuously poll for the current playing song."""
    while True:
        try:
            # Try Spotify API first (most reliable)
            spotify_data = get_spotify_api()

            if spotify_data:
                song = spotify_data["song"]
                artist = spotify_data["artist"]
                progress = spotify_data["progress_ms"]
                source = "spotify"
            else:
                # Fallback: Spotify window title
                song, artist = get_spotify_local()
                progress = 0
                source = "spotify_local"

                if not song:
                    # Fallback: YouTube Music browser tab
                    song, artist = get_youtube_music()
                    source = "youtube_music"

            if song:
                lines = fetch_lyrics(song, artist)
                lyric = get_current_lyric(progress, lines)

                state["playing"] = True
                state["song"] = song
                state["artist"] = artist
                state["lyric"] = lyric
                state["progress_ms"] = progress
                state["source"] = source

                print(f"[{source.upper()}] {artist} - {song} | {lyric[:40]}...")
            else:
                state["playing"] = False

        except Exception as e:
            print(f"[Poll Error] {e}")

        time.sleep(1)


# ─────────────────────────────────────────────
#  FLASK SERVER
# ─────────────────────────────────────────────

@app.route("/now-playing")
def now_playing():
    """
    Returns JSON that the ESP32 fetches.
    Example response:
    {
      "playing": true,
      "song": "Blinding Lights",
      "artist": "The Weeknd",
      "lyric": "I said, ooh, I'm blinded by the lights",
      "source": "spotify"
    }
    """
    return jsonify({
        "playing": state["playing"],
        "song": state["song"],
        "artist": state["artist"],
        "lyric": state["lyric"],
        "source": state["source"],
        "timestamp": int(time.time()),
    })


@app.route("/")
def index():
    return """
    <h2>🎵 ESP32 Lyrics Bridge</h2>
    <p>Server is running!</p>
    <p><a href="/now-playing">View now-playing JSON</a></p>
    """


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 50)
    print("  🎵 ESP32 Lyrics Bridge Starting...")
    print("=" * 50)

    # Start the background polling thread
    t = threading.Thread(target=poll_loop, daemon=True)
    t.start()

    print(f"\n  ✅ Server running at http://0.0.0.0:5000")
    print(f"  📡 Your ESP32 should connect to this PC's IP")
    print(f"  🔍 Test at: http://localhost:5000/now-playing\n")

    app.run(host="0.0.0.0", port=5000, debug=False)
