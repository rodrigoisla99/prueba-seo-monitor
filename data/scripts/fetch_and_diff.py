#!/usr/bin/env python3
import os
import json
import requests
import difflib
import sys

# BASE_DIR apunta a "data"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITES_CONFIG = os.path.join(BASE_DIR, "sites.json")

# carpetas
CACHE_DIR = os.path.join(BASE_DIR, "cache")
REPO_ROOT = os.path.dirname(BASE_DIR)
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
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def compare_and_save(site, filename, new_content):
    """
    Devuelve True si hubo cambios.
    También genera un archivo diff.
    """
    site_cache_dir = os.path.join(CACHE_DIR, site["name"])
    os.makedirs(site_cache_dir, exist_ok=True)

    cache_file = os.path.join(site_cache_dir, filename)
    old_content = read_file(cache_file)

    # siempre guardamos el nuevo contenido
    write_file(cache_file, new_content)

    # primera vez -> no hay comparación
    if old_content is None:
        return False

    if old_content == new_content:
        return False

    # generar diff
    diff_path = os.path.join(DIFFS_DIR, f"{site['name']}_{filename}.diff")

    diff = difflib.unified_diff(
        old_content.splitlines(),
        new_content.splitlines(),
        fromfile="old",
        tofile="new",
        lineterm=""
    )

    write_file(diff_path, "\n".join(diff))
    return True


def monitor_sites():
    sites = load_sites()
    print("=== SEO MONITOR START ===")

    for site in sites:
        print(f"\nChecking {site['name']} ({site['domain']})")

        # robots.txt
        url = site["domain"].rstrip("/") + "/robots.txt"
        status, content = fetch(url)
        if status:
            changed = compare_and_save(site, "robots.txt", content)
            print(f"robots.txt: {'CAMBIÓ' if changed else 'sin cambios'}")
        else:
            print("robots.txt: error al obtener")

        # sitemap.xml
        url = site["domain"].rstrip("/") + "/sitemap.xml"
        status, content = fetch(url)
        if status:
            changed = compare_and_save(site, "sitemap.xml", content)
            print(f"sitemap.xml: {'CAMBIÓ' if changed else 'sin cambios'}")
        else:
            print("sitemap.xml: error al obtener")

    print("\n=== SEO MONITOR END ===")


if __name__ == "__main__":
    monitor_sites()
    print(">>> DEBUG: script finalizado correctamente")
