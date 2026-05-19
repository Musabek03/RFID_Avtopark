from __future__ import annotations

import binascii
import logging
import os
import socket
import sys
import time
from pathlib import Path

import requests

try:
    from dotenv import load_dotenv  # type: ignore

    load_dotenv(Path(__file__).resolve().parent / ".env")
except Exception:  # pragma: no cover - optional dependency for the scanner host
    pass

logging.basicConfig(
    level=os.environ.get("DJANGO_LOG_LEVEL", "INFO"),
    format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("rfid-scanner")

READER_IP = os.environ.get("READER_IP", "192.168.1.100")
READER_PORT = int(os.environ.get("READER_PORT", "6000"))
DJANGO_URL = os.environ.get("DJANGO_API_URL", "http://127.0.0.1:8000/api/scan/")
SCANNER_API_TOKEN = os.environ.get("SCANNER_API_TOKEN", "")
COOLDOWN = int(os.environ.get("LOCAL_COOLDOWN_SECONDS", "5"))

COMMAND = bytes.fromhex("040001DB4B")
BUFFER_SIZE = 1024
last_scans: dict[str, float] = {}


def send_to_django(tag: str) -> None:
    headers = {"Content-Type": "application/json"}
    if SCANNER_API_TOKEN:
        headers["X-Api-Token"] = SCANNER_API_TOKEN
    try:
        response = requests.post(DJANGO_URL, json={"rfid_tag": tag}, headers=headers, timeout=2)
        if response.ok:
            data = response.json()
            logger.info("Django: %s", data.get("message", ""))
        else:
            logger.warning("Django qáteligi: %s %s", response.status_code, response.text[:200])
    except Exception as exc:
        logger.error("Sayt penen baylanısa almay atırman: %s", exc)


def main() -> None:
    logger.info("--- RFID SKANER ISKE TÚSIRILMEKTE ---")
    logger.info("Reader: %s:%s | API: %s", READER_IP, READER_PORT, DJANGO_URL)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)

    while True:
        try:
            logger.info("%s:%s adresine qosılıp atırman...", READER_IP, READER_PORT)
            sock.connect((READER_IP, READER_PORT))
            logger.info("Baylanıs ornatıldı! Skanerlenbekte...")

            while True:
                sock.send(COMMAND)
                try:
                    data = sock.recv(BUFFER_SIZE)
                    if len(data) > 8:
                        hex_data = binascii.hexlify(data).decode().upper()
                        epc_len = data[5]
                        if 4 <= epc_len <= 32 and len(data) >= 6 + epc_len:
                            epc = hex_data[12 : 12 + (epc_len * 2)]
                            if time.time() - last_scans.get(epc, 0) > COOLDOWN:
                                logger.info("BELGI: %s", epc)
                                send_to_django(epc)
                                last_scans[epc] = time.time()
                except TimeoutError:
                    pass
                time.sleep(0.1)

        except KeyboardInterrupt:
            logger.info("Shıǵıw...")
            sys.exit()
        except Exception as exc:
            logger.error("Baylanıs qáteligi: %s. 3 sekundtan soń qayta qosılıw...", exc)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            time.sleep(3)


if __name__ == "__main__":
    main()
