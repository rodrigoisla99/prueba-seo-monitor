#!/usr/bin/env python3
import os
import json
import requests
from datetime import datetime
import difflib
import sys

# BASE_DIR apunta a "data" porque el script está en data/scripts
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITES_CONFIG = os.path.join(BASE_DIR, "sites.json")

# Carpeta donde guardamos los baselines por sitio (data/cache/<Site>/...)
CACHE_DIR = os.path.join(BASE_DIR, "cache")
# Carpeta raíz del repo (un nivel arriba de data)
REPO_ROOT = os.path.dirname(BASE_DIR)
# Carpeta donde guardamos los diffs para inspeccionar (repo_root/diffs)
DIFFS_DIR = os.path.join(REPO_ROOT, "diffs")

os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(DIFFS_DIR, exist_ok=True)

def load_sites():
    if not os.path.exists(SITES_CONFIG):
        print(f"ERROR: no se encontró {SITES_CONFIG}")
        sys.exit(1)
    with open(SITES_CONFIG, "r", encoding="utf-8") as f:
        return json.load(f)

def fetch(url):
    try:
        r = requests.get(url, timeout=20)
        return r.status_code, r.text
    except Exception as e:
        return None, f"ERROR: {e}"

def read_file(path):
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()

def write_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
