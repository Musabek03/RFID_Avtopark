import socket
import time
import binascii
import requests
import json
import sys

# --- SAZLAMALAR ---
READER_IP = '192.168.1.100'
READER_PORT = 6000
DJANGO_URL = "http://127.0.0.1:8000/api/scan/"

# Wireshark-tan komanda (DB parametri menen Inventory G2)
COMMAND = bytes.fromhex("040001DB4B")
BUFFER_SIZE = 1024

# Anti-spam (sol bir mashinanı qayta jiberiwge shekemgi sekund)
COOLDOWN = 5
last_scans = {}

def send_to_django(tag):
    try:
        payload = {'rfid_tag': tag}
        response = requests.post(DJANGO_URL, json=payload, timeout=1)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Django: {data['message']}")
        else:
            print(f"⚠️ Django qáteligi: {response.status_code}")
    except Exception as e:
        print(f"❌ Sayt penen baylanisa almay atirman: {e}")

def main():
    print("--- RFID SKANER ISKE TÚSIRILMEKTE ---")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)

    while True: # Úzilgen jaǵdayda qayta qosılıw ushın máńgilik cikl
        try:
            print(f"🔌 {READER_IP} adresine qosilip atirman...")
            s.connect((READER_IP, READER_PORT))
            print("📡 Baylanis ornatildi! Skanerlenbekte...")

            while True:
                s.send(COMMAND)
                try:
                    data = s.recv(BUFFER_SIZE)
                    if len(data) > 8: # Eger uzın paket kelgen bolsa
                        # Maǵlıwmattı tallaw (Parsing)
                        hex_data = binascii.hexlify(data).decode().upper()
                        # EPC uzınlıǵın izlew (5-bayt)
                        epc_len = data[5]
                        
                        if 4 <= epc_len <= 32 and len(data) >= 6 + epc_len:
                            epc = hex_data[12 : 12 + (epc_len * 2)]
                            
                            # Waqıttı tekseriw (spam qılmaslıq ushın)
                            if time.time() - last_scans.get(epc, 0) > COOLDOWN:
                                print(f"\n🚗 BELGI: {epc}")
                                send_to_django(epc)
                                last_scans[epc] = time.time()

                except socket.timeout:
                    pass # Efirde tınıshlıq
                
                time.sleep(0.1) # Sorawlar arasındaǵı pauza

        except KeyboardInterrupt:
            print("\nShıǵıw...")
            sys.exit()
        except Exception as e:
            print(f"Baylanis qáteligi: {e}. 3 sekundtan soń qayta qosiliw...")
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            time.sleep(3)

if __name__ == "__main__":
    main()