import socket
import time
import binascii
import requests
import json
import sys

# --- НАСТРОЙКИ ---
READER_IP = '192.168.1.100'
READER_PORT = 6000
DJANGO_URL = "http://127.0.0.1:8000/api/scan/"

# Команда из Wireshark (Inventory G2 с параметром DB)
COMMAND = bytes.fromhex("040001DB4B")
BUFFER_SIZE = 1024

# Анти-спам (секунд до повторной отправки той же машины)
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
            print(f"⚠️ Ошибка Django: {response.status_code}")
    except Exception as e:
        print(f"❌ Не могу связаться с сайтом: {e}")

def main():
    print("--- ЗАПУСК RFID СКАНЕРА ---")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)

    while True: # Вечный цикл переподключения при обрыве
        try:
            print(f"🔌 Подключаюсь к {READER_IP}...")
            s.connect((READER_IP, READER_PORT))
            print("📡 Соединение установлено! Сканирую...")

            while True:
                s.send(COMMAND)
                try:
                    data = s.recv(BUFFER_SIZE)
                    if len(data) > 8: # Если пришел длинный пакет
                        # Парсинг
                        hex_data = binascii.hexlify(data).decode().upper()
                        # Ищем длину EPC (5-й байт)
                        epc_len = data[5]
                        
                        if 4 <= epc_len <= 32 and len(data) >= 6 + epc_len:
                            epc = hex_data[12 : 12 + (epc_len * 2)]
                            
                            # Проверка времени (чтобы не спамить)
                            if time.time() - last_scans.get(epc, 0) > COOLDOWN:
                                print(f"\n🚗 МЕТКА: {epc}")
                                send_to_django(epc)
                                last_scans[epc] = time.time()

                except socket.timeout:
                    pass # Тишина в эфире
                
                time.sleep(0.1) # Пауза между опросами

        except KeyboardInterrupt:
            print("\nВыход...")
            sys.exit()
        except Exception as e:
            print(f"Ошибка соединения: {e}. Реконнект через 3 сек...")
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            time.sleep(3)

if __name__ == "__main__":
    main()