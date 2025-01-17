import network
import socket
import time
from machine import Pin, reset
import ntptime
import uasyncio as asyncio
import config
import urequests
import os




# LED setup
led = Pin("LED", Pin.OUT)

# GitHub OTA Configuration
GITHUB_REPO = "SWhardfish/PiPicoW_OTA"  # Replace with your GitHub repo
BRANCH = "main"  # Branch to fetch updates from
SCRIPT_NAME = "main.py"  # Script to update

# Log file
LOG_FILE = "system_log.txt"

# Function to check if a file exists
def file_exists(filename):
    try:
        os.stat(filename)
        return True
    except OSError:
        return False

# Function to check for OTA updates
def check_for_updates():
    try:
        # GitHub API URL for the raw file
        url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/{BRANCH}/{SCRIPT_NAME}"

        # Fetch the latest version of the script
        response = urequests.get(url)

        if response.status_code == 200:
            new_code = response.text

            # Check if the new code differs from the current code
            if not file_exists(SCRIPT_NAME) or open(SCRIPT_NAME).read() != new_code:
                print("Update available. Applying update...")
                with open(SCRIPT_NAME, "w") as f:
                    f.write(new_code)
                print("Update applied. Restarting...")
                log_event("OTA update applied. Restarting...")
                machine.reset()  # Restart the device to apply the update
            else:
                print("No updates available.")
                log_event("Checked for updates: no updates available.")
        else:
            print(f"Failed to fetch update: {response.status_code}")
            log_event(f"Failed to fetch update: {response.status_code}")
    except Exception as e:
        print(f"Error during OTA update: {e}")
        log_event(f"Error during OTA update: {e}")

# Function to flash the onboard LED
def flash_led(times, delay=0.2):
    for _ in range(times):
        led.on()
        time.sleep(delay)
        led.off()
        time.sleep(delay)


# Log event function
def log_event(message, t=None):
    if t is None:
        t = time.localtime()
    formatted_time = "{:04}-{:02}-{:02} {:02}:{:02}:{:02}".format(*t)
    log_message = f"{formatted_time} - {message}"
    print(log_message)

    # Append to log file
    with open(LOG_FILE, "a") as log_file:
        log_file.write(log_message + "\n")


# Connect to Wi-Fi using credentials from config.py
async def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if not wlan.isconnected():
        print("Connecting to Wi-Fi...")
        wlan.connect(config.WIFI_SSID, config.WIFI_PASSWORD)
        for _ in range(30):  # Timeout after 30 seconds
            if wlan.isconnected():
                break
            await asyncio.sleep(1)
        else:
            print("Failed to connect to Wi-Fi")
            return None

    print("Connected to Wi-Fi")
    print("Network config:", wlan.ifconfig())
    flash_led(5, delay=0.1)
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
                flash_led(3, delay=0.5)
            else:
                print("Reconnection failed")
                log_event("Wi-Fi reconnection failed")
        await asyncio.sleep(10)  # Check every 10 seconds


# Synchronize time using NTP
async def sync_time():
    try:
        ntptime.settime()
        log_event("Time synchronized with NTP")
        flash_led(3, delay=0.3)
    except Exception as e:
        log_event(f"Error synchronizing time: {e}")


# Serve HTTP requests
async def serve(client):
    try:
        request = client.recv(1024).decode("utf-8")
        if "GET /led/on" in request:
            led.on()
            t = time.localtime()
            offset = 2 if (3 <= t[1] <= 10 and not (t[1] == 3 and t[2] < 25) and not (t[1] == 10 and t[2] >= 25)) else 1
            adjusted_time = time.mktime(t) + offset * 3600
            log_event("LED turned ON", time.localtime(adjusted_time))
            response = "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n<h1>LED ON</h1>"
            client.send(response)
        elif "GET /led/off" in request:
            led.off()
            t = time.localtime()
            offset = 2 if (3 <= t[1] <= 10 and not (t[1] == 3 and t[2] < 25) and not (t[1] == 10 and t[2] >= 25)) else 1
            adjusted_time = time.mktime(t) + offset * 3600
            log_event("LED turned OFF", time.localtime(adjusted_time))
            response = "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n<h1>LED OFF</h1>"
            client.send(response)
        elif "GET /log" in request:
            serve_log(client)
        elif "GET /update" in request:  # Add this route for OTA update
            check_for_updates()  # Trigger the OTA update check
            response = "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n<h1>OTA Update Triggered</h1>"
            client.send(response)
        else:
            response = """\
    HTTP/1.1 200 OK
    Content-Type: text/html; charset=utf-8

    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Pico W</title>
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
                background-color: grey;
            }
            .log-button:hover {
                transform: scale(1.05);
            }
            .space {
                margin-top: 20px;
            }
        </style>
        <script>
            async function toggleLED(action) {
                await fetch(`/led/${action}`);
            }

            function showLog() {
                // Get the base URL of the current page dynamically
                const baseUrl = window.location.origin;
                // Open the log page dynamically based on the current base URL
                window.open(`${baseUrl}/log`, '_blank');
            }
            
            async function triggerUpdate() {
                // Trigger OTA update check via HTTP
                await fetch('/update');
                alert('OTA update triggered. Check logs for details.');
            }
        </script>
    </head>
    <body>
        <h1>Control Onboard LED</h1>
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
            <button class="log-button" onclick="triggerUpdate()">Check for Updates</button> <!-- New button -->
        </div>
    </body>
    </html>
    """

            client.send(response)
    except Exception as e:
        log_event(f"Error: {e}", time.localtime())
    finally:
        client.close()

    # Function to serve the log
def serve_log(client):
    try:
        with open(LOG_FILE, "r") as log_file:
            logs = log_file.read()
        response = f"""\
    HTTP/1.1 200 OK
    Content-Type: text/plain

    {logs}
    """
        client.send(response)
    except Exception as e:
        log_event(f"Error serving log: {e}", time.localtime())
        response = "HTTP/1.1 500 Internal Server Error\r\nContent-Type: text/plain\r\n\r\nAn error occurred."
        client.send(response)


# Start the web server
async def start_web_server():
    addr = socket.getaddrinfo("0.0.0.0", 80)[0][-1]
    s = socket.socket()
    s.bind(addr)
    s.listen(1)
    print("Web server listening on", addr)
    log_event("Web server started")
    flash_led(2, delay=1.0)

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
    await sync_time()

    # Start the web server
    await asyncio.sleep(1)
    await start_web_server()

# Run the main async loop
try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("Program terminated")
