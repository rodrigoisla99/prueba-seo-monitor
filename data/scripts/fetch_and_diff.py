import os
import json
import requests
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
SITES_CONFIG = os.path.join(BASE_DIR, "sites.json")

os.makedirs(DATA_DIR, exist_ok=True)

def load_sites():
    with open(SITES_CONFIG, "r", encoding="utf-8") as f:
        return json.load(f)

def fetch_url(url):
    try:
        res = requests.get(url, timeout=20)
        return res.text
    except Exception as e:
        return f"ERROR: {e}"

def check_and_diff(site_name, filename, new_content):
    site_folder = os.path.join(DATA_DIR, site_name)
    os.makedirs(site_folder, exist_ok=True)

    file_path = os.path.join(site_folder, filename)

    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            old_content = f.read()
    else:
        old_content = ""

    changed = old_content != new_content

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    return changed

def monitor_sites():
    sites = load_sites()
    alerts = []

    for site in sites:
        name = site["name"]
        domain = site["domain"].rstrip("/")

        print(f"Checking {name}...")

        # --- ROBOTS.TXT ---
        robots_url = f"{domain}/robots.txt"
        robots_content = fetch_url(robots_url)
        if check_and_diff(name, "robots.txt", robots_content):
            alerts.append(f"[{name}] Cambio detectado en robots.txt")

        # --- SITEMAP.XML ---
        sitemap_url = f"{domain}/sitemap.xml"
        sitemap_content = fetch_url(sitemap_url)
        if check_and_diff(name, "sitemap.xml", sitemap_content):
            alerts.append(f"[{name}] Cambio detectado en sitemap.xml")

    # Print alerts for GitHub Actions
    if alerts:
        print("\n=== CAMBIOS DETECTADOS ===")
        for a in alerts:
            print(a)
    else:
        print("Sin cambios detectados.")

if __name__ == "__main__":
    monitor_sites()
