import network
import socket
import time
from machine import Pin, reset
import ntptime
import uasyncio as asyncio
import config
import urequests
import uos

# MOSFET control setup - replace with your actual GPIO pin
MOSFET_PIN = 0  # Change this to the GPIO pin connected to your MOSFET gate
mosfet = Pin(MOSFET_PIN, Pin.OUT)
mosfet.off()  # Start with LED strip off

# Log file
LOG_FILE = "system_log3.txt"
MAX_LOG_SIZE = 10 * 1024  # Maximum log file size in bytes (e.g., 10 KB)

# GitHub OTA Configuration
GITHUB_REPO = "SWhardfish/PiPicoW_OTA"  # Replace with your GitHub repo
BRANCH = "main"  # Branch to fetch updates from
SCRIPT_NAME = "main.py"  # Script to update


# Check if file exists
def file_exists(path):
    try:
        uos.stat(path)
        return True
    except OSError:
        return False


# Function to normalize script content
def normalize_code(code):
    """Normalize code by stripping trailing spaces and converting line endings to '\n'."""
    return "\n".join(line.rstrip() for line in code.splitlines())


def flash_led(times=None, delay=0.2, pattern=None):
    """
    Flash the onboard LED with either a simple repeating pattern or a custom pattern.
    This is now only used for status indications, not for LED strip control.

    :param times: Number of times to flash the LED (used for simple blinking).
    :param delay: Delay between flashes for simple blinking.
    :param pattern: Custom pattern as a list of (state, duration) tuples.
                    Example: [(1, 5.0), (0, 0.5), (1, 0.1)]
    """
    led = Pin("LED", Pin.OUT)  # Onboard LED for status only
    if pattern:
        # Use the custom pattern
        for state, duration in pattern:
            led.value(state)
            time.sleep(duration)
    elif times is not None:
        # Use the simple blinking pattern
        for _ in range(times):
            led.on()
            time.sleep(delay)
            led.off()
            time.sleep(delay)
    led.off()  # Ensure LED is off when done


# Function to check for OTA updates
def check_for_updates():
    try:
        # GitHub API URL for the raw file
        url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/{BRANCH}/{SCRIPT_NAME}"

        # Fetch the latest version of the script
        response = urequests.get(url)

        if response.status_code == 200:
            new_code = normalize_code(response.text)

            # Check if the new code differs from the current code
            if not file_exists(SCRIPT_NAME):
                print("No existing script found. Applying update...")
                update_script(new_code)
            else:
                with open(SCRIPT_NAME, "r") as f:
                    current_code = normalize_code(f.read())
                if current_code != new_code:
                    print("Update available. Applying update...")
                    flash_led(pattern=[(1, 5.0), (0, 0.5), (1, 0.1), (0, 0.5), (1, 5.0)])
                    t = time.localtime()
                    offset = 2 if (3 <= t[1] <= 10 and not (t[1] == 3 and t[2] < 25) and not (t[1] == 10 and t[2] >= 25) else 1
                    adjusted_time = time.mktime(t) + offset * 3600
                    log_event("Update available. Applying update...", time.localtime(adjusted_time))
                    update_script(new_code)
                    else:
                    print("No updates available.")
                    t = time.localtime()
                    offset = 2 if (3 <= t[1] <= 10 and not (t[1] == 3 and t[2] < 25) and not (t[1] == 10 and t[2] >= 25) else 1
                    adjusted_time = time.mktime(t) + offset * 3600
                    log_event("Checked for updates: No updates available.", time.localtime(adjusted_time))
                    else:
                    print(f"Failed to fetch update: {response.status_code}")
                    t = time.localtime()
                    offset = 2 if (3 <= t[1] <= 10 and not (t[1] == 3 and t[2] < 25) and not (t[1] == 10 and t[2] >= 25) else 1
                    adjusted_time = time.mktime(t) + offset * 3600
                    log_event(f"Failed to fetch update: {response.status_code}", time.localtime(adjusted_time))
    except Exception as e:
        print(f"Error during OTA update: {e}")
        t = time.localtime()
        offset = 2 if (3 <= t[1] <= 10 and not (t[1] == 3 and t[2] < 25) and not (t[1] == 10 and t[2] >= 25) else 1
        adjusted_time = time.mktime(t) + offset * 3600
        log_event(f"Error during OTA update: {e}", time.localtime(adjusted_time))

        # Function to update the script and restart


def update_script(new_code):
    with open(SCRIPT_NAME, "w") as f:
        f.write(new_code)
    print("Update applied. Restarting...")
    t = time.localtime()
    offset = 2 if (3 <= t[1] <= 10 and not (t[1] == 3 and t[2] < 25) and not (t[1] == 10 and t[2] >= 25)) else 1
    adjusted_time = time.mktime(t) + offset * 3600
    log_event("OTA update applied. Restarting...", time.localtime(adjusted_time))
    machine.reset()  # Restart the device to apply the update


# Log event function
def log_event(message, t=None):
    try:
        if t is None:
            t = time.localtime()
        formatted_time = "{:04}-{:02}-{:02} {:02}:{:02}:{:02}".format(*t)
        log_message = f"{formatted_time} - {message}"
        print(log_message)

        # Check if log file exists and its size
        if file_exists(LOG_FILE) and uos.stat(LOG_FILE)[6] >= MAX_LOG_SIZE:
            print("Log file size exceeded, rotating log file.")
            t = time.localtime()
            offset = 2 if (3 <= t[1] <= 10 and not (t[1] == 3 and t[2] < 25) and not (t[1] == 10 and t[2] >= 25)) else 1
            adjusted_time = time.mktime(t) + offset * 3600
            log_event("Log file size exceeded, rotating log file.", time.localtime(adjusted_time))
            rotate_log_file()

        # Append the message to the log file
        with open(LOG_FILE, "a") as log_file:
            log_file.write(log_message + "\n")

    except Exception as e:
        print(f"Error logging event: {e}")


# Rotate log file function
def rotate_log_file():
    try:
        # Create a backup of the current log file
        if file_exists(LOG_FILE):
            uos.rename(LOG_FILE, LOG_FILE + ".bak")
            print("Log file rotated. Old log saved as system_log.txt.bak")
    except Exception as e:
        print(f"Error rotating log file: {e}")


# Connect to Wi-Fi using credentials from config.py
async def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.config(pm=0)  # Disable Wi-Fi power saving

    if not wlan.isconnected():
        print("Connecting to Wi-Fi...")
        log_event("Connecting to Wi-Fi...")
        wlan.connect(config.WIFI_SSID, config.WIFI_PASSWORD)
        for _ in range(30):  # Timeout after 30 seconds
            if wlan.isconnected():
                break
            await asyncio.sleep(1)
        else:
            print("Failed to connect to Wi-Fi")
            log_event("Failed to connect to Wi-Fi")
            return None

    print("Connected to Wi-Fi")
    ip_address = wlan.ifconfig()[0]  # Extract IP address
    print("Network config:", wlan.ifconfig())
    log_event(f"Connected to Wi-Fi, IP address: {ip_address}")
    flash_led(times=7, delay=0.1)
    return wlan


# Monitor Wi-Fi connection
async def monitor_wifi(wlan, ssid, password):
    while True:
        if not wlan.isconnected():
            print("Wi-Fi disconnected! Reconnecting...")
            log_event("Wi-Fi disconnected, attempting reconnection")
            wlan.connect(config.WIFI_SSID, config.WIFI_PASSWORD)
            for _ in range(30):  # Timeout after 30 seconds
                if wlan.isconnected():
                    break
                await asyncio.sleep(1)
            if wlan.isconnected():
                print("Wi-Fi reconnected!")
                log_event("Wi-Fi reconnected")
                flash_led(times=3, delay=0.5)
            else:
                print("Reconnection failed")
                log_event("Wi-Fi reconnection failed")
        await asyncio.sleep(10)  # Check every 10 seconds


# Synchronize time using NTP with retry
async def sync_time(max_retries=3, retry_delay=5):
    retries = 0
    while retries < max_retries:
        try:
            # Attempt to synchronize time
            ntptime.settime()
            t = time.localtime()
            offset = 2 if (3 <= t[1] <= 10 and not (t[1] == 3 and t[2] < 25) and not (t[1] == 10 and t[2] >= 25)) else 1
            adjusted_time = time.mktime(t) + offset * 3600
            log_event("Time synchronized with NTP", time.localtime(adjusted_time))
            flash_led(times=3, delay=0.3)
            return  # Exit the function if successful
        except Exception as e:
            retries += 1
            log_event(f"Error synchronizing time (attempt {retries}): {e}")
            if retries < max_retries:
                await asyncio.sleep(retry_delay)  # Wait before retrying
            else:
                # Log final failure after exhausting retries
                t = time.localtime()
                offset = 2 if (3 <= t[1] <= 10 and not (t[1] == 3 and t[2] < 25) and not (t[1] == 10 and t[2] >= 25)) else 1
                adjusted_time = time.mktime(t) + offset * 3600
                log_event("Failed to synchronize time after multiple attempts", time.localtime(adjusted_time))
                flash_led(times=5, delay=0.3)  # Indicate failure with 5 LED flashes


# Serve HTTP requests
async def serve(client):
    try:
        request = client.recv(1024).decode("utf-8")
        if "GET /led/on" in request:
            mosfet.on()
            t = time.localtime()
            offset = 2 if (3 <= t[1] <= 10 and not (t[1] == 3 and t[2] < 25) and not (t[1] == 10 and t[2] >= 25)) else 1
            adjusted_time = time.mktime(t) + offset * 3600
            log_event("LED Strip turned ON", time.localtime(adjusted_time))
            response = "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n<h1>LED Strip ON</h1>"
            client.send(response)
        elif "GET /led/off" in request:
            mosfet.off()
            t = time.localtime()
            offset = 2 if (3 <= t[1] <= 10 and not (t[1] == 3 and t[2] < 25) and not (t[1] == 10 and t[2] >= 25)) else 1
            adjusted_time = time.mktime(t) + offset * 3600
            log_event("LED Strip turned OFF", time.localtime(adjusted_time))
            response = "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n<h1>LED Strip OFF</h1>"
            client.send(response)
        elif "GET /log" in request:
            serve_log(client)
        elif "GET /ota-update" in request:
            try:
                # Trigger the OTA update check
                t = time.localtime()
                offset = 2 if (3 <= t[1] <= 10 and not (t[1] == 3 and t[2] < 25) and not (t[1] == 10 and t[2] >= 25)) else 1
                adjusted_time = time.mktime(t) + offset * 3600
                log_event("Manual OTA update check triggered via web.", time.localtime(adjusted_time))
                update_status = check_for_updates()
                response = f"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\n{update_status}"
            except Exception as e:
                t = time.localtime()
                offset = 2 if (3 <= t[1] <= 10 and not (t[1] == 3 and t[2] < 25) and not (t[1] == 10 and t[2] >= 25)) else 1
                adjusted_time = time.mktime(t) + offset * 3600
                log_event(f"Error during manual OTA update: {e}", time.localtime(adjusted_time))
                response = "HTTP/1.1 500 Internal Server Error\r\nContent-Type: text/plain\r\n\r\nError checking for updates."
            client.send(response)
        else:
            response = """\
HTTP/1.1 200 OK
Content-Type: text/html; charset=utf-8

<!DOCTYPE html>
<html lang="en">
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pico W LED Strip Control</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            text-align: center;
            margin: 0;
            padding: 0;
            background: linear-gradient(to top, #003366, #66aaff);
            color: white;
            height: 100vh;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
        }
        .button-container {
            display: flex;
            justify-content: center;
            gap: 20px;
        }
        button {
            width: 120px;
            height: 50px;
            font-size: 16px;
            font-weight: bold;
            background-color: #4CAF50;
            color: white;
            border: none;
            border-radius: 10px;
            cursor: pointer;
        }
        button:hover {
            transform: scale(1.05);
        }
        .on-button {
            font-size: 26px;
            background-color: #4CAF50;
        }
        .off-button {
            font-size: 26px;
            background-color: #f44336;
        }
        .log-button {
            width: 120px;
            height: 25px;
            font-size: 16px;
            background-color: black;
        }
        .log-button:hover {
            transform: scale(1.05);
        }
        .space {
            margin-top: 20px;
        }
        .status-message {
            margin-top: 20px;
            font-size: 18px;
            color: #ffffff;
            text-align: center;
        }
        .status-indicator {
            margin-top: 20px;
            width: 100px;
            height: 100px;
            border-radius: 50%;
            margin: 20px auto;
            background-color: #f44336;
            box-shadow: 0 0 20px #f44336;
        }
        .status-indicator.on {
            background-color: #4CAF50;
            box-shadow: 0 0 20px #4CAF50;
        }
    </style>
    <script>
        async function toggleLED(action) {
            await fetch(`/led/${action}`);
            updateStatusIndicator();
        }

        function showLog() {
            const baseUrl = window.location.origin;
            window.open(`${baseUrl}/log`, '_blank');
        }

        async function triggerUpdate() {
            try {
                const response = await fetch('/ota-update');
                const result = await response.text();
                document.getElementById('update-message').innerText = result;
            } catch (error) {
                document.getElementById('update-message').innerText = 'Failed to check for updates. Try again later.';
            }
        }

        async function updateStatusIndicator() {
            try {
                const response = await fetch('/led/status');
                const status = await response.text();
                const indicator = document.getElementById('led-status');
                indicator.className = status === 'on' ? 'status-indicator on' : 'status-indicator';
            } catch (error) {
                console.error('Error fetching LED status:', error);
            }
        }

        // Check LED status on page load
        document.addEventListener('DOMContentLoaded', updateStatusIndicator);
    </script>
</head>
<body>
    <h1>Pi Pico W LED Strip Control</h1>
    <div id="led-status" class="status-indicator"></div>
    <div class="button-container">
        <button class="on-button" onclick="toggleLED('on')">ON</button>
        <button class="off-button" onclick="toggleLED('off')">OFF</button>
    </div>
    <div class="space"></div>
    <div class="button-container">
        <button class="log-button" onclick="showLog()">Show Log</button>
    </div>
    <div class="space"></div>
    <div class="button-container">
        <button class="log-button" onclick="triggerUpdate()">SW Updates</button>
    </div>
    <div class="status-message" id="update-message"></div>
</body>
</html>
"""
            client.send(response)
    except Exception as e:
        log_event(f"Error: {e}", time.localtime())
    finally:
        client.close()


# Serve log function
def serve_log(client):
    try:
        if not file_exists(LOG_FILE):
            raise FileNotFoundError("Log file does not exist.")

        with open(LOG_FILE, "r") as log_file:
            logs = log_file.read()
        response = f"""\
HTTP/1.1 200 OK
Content-Type: text/plain

{logs}
"""
        client.send(response)
    except FileNotFoundError as e:
        print(f"Error serving log: {e}")
        response = "HTTP/1.1 404 Not Found\r\nContent-Type: text/plain\r\n\r\nLog file not found."
        client.send(response)
    except Exception as e:
        print(f"Error serving log: {e}")
        response = "HTTP/1.1 500 Internal Server Error\r\nContent-Type: text/plain\r\n\r\nAn error occurred."
        client.send(response)


# Start the web server
async def start_web_server():
    addr = socket.getaddrinfo("0.0.0.0", 80)[0][-1]
    s = socket.socket()
    s.bind(addr)
    s.listen(1)
    print("Web server listening on", addr)
    t = time.localtime()
    offset = 2 if (3 <= t[1] <= 10 and not (t[1] == 3 and t[2] < 25) and not (t[1] == 10 and t[2] >= 25)) else 1
    adjusted_time = time.mktime(t) + offset * 3600
    log_event("Web server started", time.localtime(adjusted_time))
    flash_led(times=2, delay=1.0)

    while True:
        client, addr = s.accept()
        print("Client connected from", addr)
        await serve(client)


# Main async function
async def main():
    # Use Wi-Fi credentials from config.py
    wlan = await connect_wifi()
    if wlan is None:
        print("Exiting: Unable to connect to Wi-Fi")
        return

    # Check for updates before starting the main app
    check_for_updates()

    # Start Wi-Fi monitoring
    asyncio.create_task(monitor_wifi(wlan, config.WIFI_SSID, config.WIFI_PASSWORD))

    # Synchronize time
    await asyncio.sleep(1)
    await sync_time(max_retries=5, retry_delay=10)

    # Start the web server
    await asyncio.sleep(1)
    await start_web_server()


# Run the main async loop
try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("Program terminated")