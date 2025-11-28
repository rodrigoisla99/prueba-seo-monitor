import os
import requests
import difflib
import json

CACHE_DIR = "data/cache"
DIFF_DIR = "diffs"

os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(DIFF_DIR, exist_ok=True)

def download(url):
    try:
        r = requests.get(url, timeout=20)
        if r.status_code == 200:
            return r.text
        return None
    except Exception:
        return None

def check_and_diff(name, domain, filename):
    print(f"\n--- Procesando {name} - {filename} ---")

    url = f"{domain}/{filename}"
    content = download(url)

    if content is None:
        print(f"⚠ No se pudo descargar {url}")
        return

    # archivos históricos
    cached_path = f"{CACHE_DIR}/{name}_{filename}"
    new_path = f"{CACHE_DIR}/{name}_{filename}.new"

    # guardar archivo nuevo temporal
    with open(new_path, "w", encoding="utf-8") as f:
        f.write(content)

    # si no existe versión anterior → primera ejecución (no hay diff)
    if not os.path.exists(cached_path):
        os.replace(new_path, cached_path)
        print(f"Primera vez: guardado {cached_path}")
        return

    # cargar ambas versiones
    with open(cached_path, "r", encoding="utf-8") as old_file:
        old_content = old_file.readlines()

    with open(new_path, "r", encoding="utf-8") as new_file:
        new_content = new_file.readlines()

    # generar diff
    diff = list(difflib.unified_diff(
        old_content,
        new_content,
        fromfile="old",
        tofile="new",
        lineterm=""
    ))

    # si no hay cambios
    if len(diff) == 0:
        print("No hay cambios detectados.")
        os.remove(new_path)
        return

    print("⚠ CAMBIO DETECTADO — diff generado")

    # guardar diff
    diff_file = f"{DIFF_DIR}/{name}_{filename}_diff.txt"
    with open(diff_file, "w", encoding="utf-8") as d:
        d.write("\n".join(diff))

    print(f"Diff guardado en: {diff_file}")

    # reemplazar archivo anterior por el nuevo
    os.replace(new_path, cached_path)


def main():
    with open("data/sites.json", "r", encoding="utf-8") as f:
        sites = json.load(f)

    for site in sites:
        name = site["name"]
        domain = site["domain"]

        check_and_diff(name, domain, "robots.txt")
        check_and_diff(name, domain, "sitemap.xml")


if __name__ == "__main__":
    main()
