import uasyncio as asyncio
import machine, network, time, json, ntptime, dht
from machine import Pin
from neopixel import NeoPixel

# --- Ρυθμίσεις ---
WIFI_SSID = "theo"
WIFI_PASSWORD = "21040672bill"
LED_PIN = 21
NUM_LEDS = 10
SENSOR_PIN = 22
LOG_FILE = "log.json"

np = NeoPixel(Pin(LED_PIN), NUM_LEDS)
sensor = dht.DHT22(Pin(SENSOR_PIN))
ram_logs = []
last_save_hour = -1

state = {
    "led_on": True,
    "auto": True,
    "brightness": 0.5,
    "temperature": 0.0,
    "humidity": 0.0,
    "manual_color": [255, 255, 255]
}
current = [0,0,0]

async def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)
    
    print("Προσπάθεια σύνδεσης στο WiFi...", end="")
    while not wlan.isconnected():
        print(".", end="")
        await asyncio.sleep(1)
    
    # Λήψη των ρυθμίσεων δικτύου
    ip_address = wlan.ifconfig()[0]
    
    print("\n" + "="*30)
    print("Συνδέθηκε επιτυχώς!")
    print(f"Τοπική IP: http://{ip_address}")
    print("="*30)
    
    # Συγχρονισμός ώρας μέσω NTP
    try:
        ntptime.settime()
        print("Η ώρα συγχρονίστηκε μέσω NTP.")
    except:
        print("Αποτυχία συγχρονισμού NTP.")

def get_greek_time():
    # Λήψη UTC χρόνου από το σύστημα
    t = time.localtime() # (year, month, mday, hour, minute, second, weekday, yearday)
    
    # Η Ελλάδα είναι UTC+2 το χειμώνα και UTC+3 το καλοκαίρι
    # Απλοποιημένος κανόνας για θερινή ώρα: Από Απρίλιο έως Οκτώβριο (χονδρικά)
    # Για απόλυτη ακρίβεια χρειάζεται έλεγχος τελευταίας Κυριακής, 
    # αλλά το παρακάτω καλύπτει το 95% των περιπτώσεων:
    offset = 3 if 3 < t[1] < 11 else 2
    
    # Δημιουργία timestamp, πρόσθεση των ωρών και μετατροπή ξανά σε tuple
    greek_seconds = time.mktime(t) + (offset * 3600)
    return time.localtime(greek_seconds)

def get_sun_color(hour, minute):
    # Μετατροπή σε λεπτά ημέρας (0-1439)
    now = hour * 60 + minute
    #print (now)
    if now < 360:      # 00:00 - 06:00: Βαθύ Μπλε (Νύχτα)
        return [0, 0, 15]
    elif now < 480:    # 06:00 - 08:00: Ανατολή (Πορτοκαλί)
        return [180, 60, 0]
    elif now < 1080:   # 08:00 - 18:00: Φως Ημέρας (Θερμό Λευκό)
        return [210, 210, 160]
    elif now < 1200:   # 18:00 - 20:00: Δύση (Κόκκινο/Πορτοκαλί)
        return [180, 40, 0]
    else:              # 20:00 - 00:00: Νύχτα
        return [0, 0, 15]

async def led_task():
    global current
    while True:
        if not state["led_on"]:
            target = [0, 0, 0]
        elif state["auto"]:
            # Λήψη πραγματικής ώρας από τον Pico
            t = get_greek_time()
            #print ('Ώρα:',t)
            target = get_sun_color(t[3], t[4])
        else:
            # Χειροκίνητη λειτουργία
            target = [int(c * state["brightness"]) for c in state["manual_color"]]

        # Smooth Transition Logic
        for i in range(3):
            diff = target[i] - current[i]
            if abs(diff) < 1:
                current[i] = target[i]
            else:
                # 0.05 = πολύ ομαλή αλλαγή. Αν το θες πιο γρήγορο βάλε 0.1
                current[i] += diff * 0.05

        # Ενημέρωση των LED
        color = (int(current[0]), int(current[1]), int(current[2]))
        #print('Χρώμα:',color)
        for i in range(NUM_LEDS):
            np[i] = color
        np.write()
        
        await asyncio.sleep_ms(50)

async def sensor_task():
    global last_save_hour, ram_logs
    while True:
        try:
            sensor.measure()
            state["temperature"] = round(sensor.temperature(), 1)
            state["humidity"] = round(sensor.humidity(), 1)
            
            # Αποθήκευση στη RAM
            entry = {"temp": state["temperature"], "hum": state["humidity"]}
            ram_logs.append(entry)
            if len(ram_logs) > 300: ram_logs.pop(0)

            # Αποθήκευση στη Flash μία φορά την ώρα
            current_hour = get_greek_time()[3]
            if current_hour != last_save_hour:
                save_logs_to_file()
                last_save_hour = current_hour
                
        except Exception as e: print("Sensor error:", e)
        await asyncio.sleep(30)

def save_logs_to_file():
    try:
        with open(LOG_FILE, "w") as f:
            json.dump(ram_logs, f)
        print("Logs saved to Flash")
    except Exception as e: print("File save error:", e)

async def serve(reader, writer):
    try:
        line = await reader.readline()
        if not line: return
        req = line.decode().split()
        if len(req) < 2: return
        method, full_path = req[0], req[1]
        
        while True:
            h = await reader.readline()
            if h == b"\r\n" or h == b"": break

        path = full_path.split("?")[0]
        query = full_path.split("?")[1] if "?" in full_path else ""

        if path.startswith("/api/"):
            res = {} # Αυτή η μεταβλητή πρέπει να γεμίσει
            if path == "/api/state":
                res = state
            elif path == "/api/logs":
                res = ram_logs # Διορθώθηκε από res_data σε res
            elif path == "/api/toggle":
                state["led_on"] = not state["led_on"]
                res = {"led_on": state["led_on"]}
            elif path == "/api/auto":
                state["auto"] = not state["auto"]
                res = {"auto": state["auto"]}
            elif path == "/api/brightness":
                state["brightness"] = float(query.split("=")[1])
                res = {"ok": True}
            elif path == "/api/set_color":
                params = dict([p.split("=") for p in query.split("&")])
                state["manual_color"] = [int(params['r']), int(params['g']), int(params['b'])]
                state["auto"] = False
                res = {"ok": True}
            
            await writer.awrite("HTTP/1.0 200 OK\r\nContent-Type: application/json\r\n\r\n" + json.dumps(res))
        else:
            fname = "index.html" if path == "/" else path.lstrip("/")
            try:
                with open(fname, "r") as f:
                    content = f.read()
                ctype = "text/html" if fname.endswith(".html") else "application/javascript"
                await writer.awrite(f"HTTP/1.0 200 OK\r\nContent-Type: {ctype}\r\n\r\n" + content)
            except:
                await writer.awrite("HTTP/1.0 404 Not Found\r\n\r\n404")
        await writer.aclose()
    except: pass

async def main():
    await connect_wifi()
    asyncio.create_task(led_task())
    asyncio.create_task(sensor_task())
    await asyncio.start_server(serve, "0.0.0.0", 80)
    while True:
        await asyncio.sleep(1)

try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("\nΤο πρόγραμμα διακόπηκε από το χρήστη.")
finally:	# Εκτελείται σε κάθε περίπτωση
    print("Σβήσιμο LED και καθαρισμός...")
    for i in range(NUM_LEDS):
        np[i] = (0, 0, 0)
    np.write()
    time.sleep(0.1)