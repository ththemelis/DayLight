import uasyncio as asyncio
import machine, network, time, json, ntptime, dht
from machine import Pin
from neopixel import NeoPixel

# --- Φόρτωση Ρυθμίσεων από το αρχείο JSON ---
try:
    with open("settings.json", "r") as f:
        config = json.load(f)
except Exception as e:
    print("Σφάλμα ανάγνωσης settings.json:", e)

np = NeoPixel(Pin(config["LED_PIN"]), config["NUM_LEDS"])
sensor = dht.DHT22(Pin(config["SENSOR_PIN"]))
NUM_LEDS = config["NUM_LEDS"]

state = {
    "led_on": True,
    "auto": True,
    "brightness": 0.5,
    "temperature": 0.0,
    "humidity": 0.0,
    "manual_color": [255, 255, 255]
}
current = [0,0,0]

# Συνάρτηση για την σύνδεση στο WIFI
async def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(config["WIFI_SSID"], config["WIFI_PASSWORD"])
    
    print("Προσπάθεια σύνδεσης στο WiFi...", end="")
    while not wlan.isconnected():
        print(".", end="")
        await asyncio.sleep(1)
    
    ip_address = wlan.ifconfig()[0] # Λήψη των ρυθμίσεων δικτύου
    
    print("\n" + "="*30)
    print("Συνδέθηκε επιτυχώς!")
    print(f"Διεύθυνση IP: http://{ip_address}")
    print("="*30)
    
    try: # Συγχρονισμός ώρας μέσω NTP
        ntptime.settime()
        print("Η ώρα συγχρονίστηκε μέσω NTP.")
    except:
        print("Αποτυχία συγχρονισμού NTP.")

# Συνάρτηση λήψης ώρας Ελλάδας
def get_greek_time():
    # Λήψη UTC χρόνου από το σύστημα
    t = time.localtime() # (year, month, mday, hour, minute, second, weekday, yearday)
    
    # Η Ελλάδα είναι UTC+2 το χειμώνα και UTC+3 το καλοκαίρι
    # Από Απρίλιο έως Οκτώβριο θερινή ώρα
    # Για απόλυτη ακρίβεια χρειάζεται έλεγχος τελευταίας Κυριακής
    if 3 < t[1] < 11:
        offset = 3
    else:
        offset = 2
    
    # Δημιουργία timestamp, πρόσθεση των ωρών και μετατροπή ξανά σε tuple
    greek_seconds = time.mktime(t) + (offset * 3600)
    return time.localtime(greek_seconds)

# Συνάρτηση υπολογισμού χρώματος LED, ανάλογα με την ώρα
def get_sun_color(hour, minute):
    now = hour * 60 + minute # Μετατροπή της ώρας σε λεπτά (0-1439)
    #print (now)
    if now < 300:      # 00:00 - 05:00: (Βαθιά Νύχτα)
        return [5, 5, 20]
    elif now < 390:    # 05:00 - 06:30: (Λυκαυγές)
        return [40, 40, 80]
    elif now < 450:   # 06:30 - 07:30: (Ανατολή)
        return [255, 140, 40]
    elif now < 570:   # 07:30 - 09:30: ()
        return [255, 210, 150]
    elif now < 720:   # 09:30 - 12:00: ()
        return [255, 245, 230]
    elif now < 900:   # 12:30 - 15:00: ()
        return [255, 255, 255]
    elif now < 1080:   # 15:00 - 18:00: ()
        return [255, 240, 210]
    elif now < 1170:   # 18:00 - 19:30: ()
        return [255, 120, 20]
    elif now < 1260:   # 19:30 - 21:00: ()
        return [80, 50, 100]
    else: # 20:00 - 00:00: Νύχτα
        return [15, 15, 40]

# Συνάρτηση χειρισμού LED
async def led_task():
    global current
    while True:
        if not state["led_on"]:
            target = [0, 0, 0]
        elif state["auto"]: # Αυτόματη λειτουργία
            t = get_greek_time() # Λήψη πραγματικής ώρας
            #print ('Ώρα:',t)
            target = get_sun_color(t[3], t[4])
        else: # Χειροκίνητη λειτουργία
            target = [int(c * state["brightness"]) for c in state["manual_color"]]

        # Ενημέρωση των LED
        color = (int(target[0]), int(target[1]), int(target[2]))
        #print('Χρώμα:',color)
        for i in range(NUM_LEDS): 
            np[i] = color
        np.write() # Αποστολή του χρώματος στα LED
        
        await asyncio.sleep_ms(50)

# Συνάρτηση λήψης τιμών από τον αισθητήρα
async def sensor_task():
    while True:
        try:
            sensor.measure() # Λήψη μετρήσεων από τον αισθητήρα
            state["temperature"] = round(sensor.temperature(), 1)
            state["humidity"] = round(sensor.humidity(), 1)         
        except Exception as e:
            print("Sensor error:", e)
            
        await asyncio.sleep(30)

async def serve(reader, writer):
    try:
        line = await reader.readline()
        if not line:
            return
        req = line.decode().split()
        if len(req) < 2:
            return
        method, full_path = req[0], req[1]
        
        while True:
            h = await reader.readline()
            if h == b"\r\n" or h == b"":
                break

        path = full_path.split("?")[0]
        query = full_path.split("?")[1] if "?" in full_path else ""

        if path.startswith("/api/"):
            res = {} # Αυτή η μεταβλητή πρέπει να γεμίσει
            if path == "/api/state":
                res = state
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
finally: # Εκτελείται σε κάθε περίπτωση
    print("Σβήσιμο LED και καθαρισμός...")
    for i in range(NUM_LEDS):
        np[i] = (0, 0, 0)
    np.write()
    time.sleep(0.1)