import os
import requests
import difflib
import json
import urllib3
import ssl
from datetime import datetime

# Silenciar warnings de verify=False
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CACHE_DIR = "data/cache"
DIFF_DIR = "diffs"

os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(DIFF_DIR, exist_ok=True)

# ---------------------------------------------------------------------
# DESCARGA PRO con:
# retry x3, headers, manejo SSL, logs claros
# ---------------------------------------------------------------------
def download(url, max_retries=3):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
        )
    }

    for attempt in range(1, max_retries + 1):
        try:
            r = requests.get(url, headers=headers, timeout=20, verify=False)

            if r.status_code == 200:
                return r.text

            print(f"⚠ [{url}] HTTP {r.status_code} — intento {attempt}/{max_retries}")

        except requests.exceptions.SSLError as e:
            print(f"❌ ERROR SSL en {url}")
            print(f"   Detalle: {str(e)}")
            return None

        except requests.exceptions.RequestException as e:
            print(f"⚠ Error de red descargando {url} — intento {attempt}/{max_retries}")
            print(f"   Detalle: {str(e)}")

    print(f"❌ No se pudo descargar {url} tras {max_retries} intentos.")
    return None

# ---------------------------------------------------------------------
# GENERA DIFF
# ---------------------------------------------------------------------
def generate_diff(old_lines, new_lines, name, target):
    diff = list(difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile="old",
        tofile="new",
        lineterm=""
    ))

    if not diff:
        return None

    diff_path = f"{DIFF_DIR}/{name}_{target}_diff_{datetime.today().strftime('%Y%m%d_%H%M%S')}.txt"

    with open(diff_path, "w", encoding="utf-8") as d:
        d.write("\n".join(diff))

    return diff_path

# ---------------------------------------------------------------------
# PROCESA ROBOTS / SITEMAP
# ---------------------------------------------------------------------
def check_and_diff(name, url, target):
    print("\n-------------------------------------------")
    print(f"Procesando: {name} → {target}")
    print("-------------------------------------------")

    content = download(url)
