import os
import requests
import difflib
import json
from urllib.parse import urljoin

CACHE_DIR = "data/cache"
DIFF_DIR = "diffs"

os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(DIFF_DIR, exist_ok=True)


# -----------------------------------------------------------
# DESCARGA ROBUSTA
# -----------------------------------------------------------
def download(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (SEO-Monitor-Bot; +https://github.com/tu-repo)"
    }

    try:
        r = requests.get(url, headers=headers, timeout=20, allow_redirects=True, verify=False)

        if r.status_code >= 400:
            print(f"  ❌ Error HTTP {r.status_code} al descargar {url}")
            return None

        return r.text

    except Exception as e:
        print(f"  ❌ Excepción al descargar {url}: {e}")
        return None


# -----------------------------------------------------------
# NORMALIZACIÓN PARA EVITAR FALSOS POSITIVOS
# -----------------------------------------------------------
def normalize(text):
    if not text:
        return ""
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    lines = [line.rstrip() for line in text.split("\n")]
    return "\n".join(lines).strip()


# -----------------------------------------------------------
# DIFFS ÚTILES
# -----------------------------------------------------------
def generate_diff(old, new, short=False):
    old_lines = old.splitlines()
    new_lines = new.splitlines()

    if short:
        differ = difflib.Differ()
        diff = [l for l in differ.compare(old_lines, new_lines) if l.startswith("+ ") or l.startswith("- ")]
        return "\n".join(diff) if diff else None

    else:
        diff = list(difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile="old",
            tofile="new",
            lineterm=""
        ))
        return "\n".join(diff) if diff else None


# -----------------------------------------------------------
# PROCESAR RECURSO (robots, sitemap, lo que sea)
# -----------------------------------------------------------
def check_and_diff(name, domain, filename):
    print(f"\n🔎 Procesando {name} → {filename}")

    # Construir URL
    url = urljoin(domain + "/", filename)

    content = download(url)
    if content is None:
        print(f"  ⚠ No se pudo descargar {url}")
        return

    # Normalización
    clean_new = normalize(content)

    # Rutas de archivo
    cache_file = f"{CACHE_DIR}/{name}_{filename}"
    new_temp = f"{CACHE_DIR}/{name}_{filename}.new"

    # Guardar versión nueva temporal
    with open(new_temp, "w", encoding="utf-8") as f:
        f.write(clean_new)

    # Primera ejecución
    if not os.path.exists(cache_file):
        os.replace(new_temp, cache_file)
        print("  🟢 Primera ejecución: archivo guardado.")
        return

    # Leer versión anterior
    with open(cache_file, "r", encoding="utf-8") as f:
        old_clean = f.read()

    # Comparación
    if old_clean == clean_new:
        print("  ✔ Sin cambios detectados.")
        os.remove(new_temp)
        return

    print("  ⚠ CAMBIO DETECTADO!")

    # Diffs
    short = generate_diff(old_clean, clean_new, short=True)
    full = generate_diff(old_clean, clean_new, short=False)

    diff_path = f"{DIFF_DIR}/{name}_{filename}_diff.txt"

    with open(diff_path, "w", encoding="utf-8") as d:
        d.write(full)

    print(f"  📝 Diff guardado: {diff_path}")

    print("\n  ---- RESUMEN DEL CAMBIO ----")
    print(short)
    print("  ----------------------------\n")

    # Reemplazar versión guardada
    os.replace(new_temp, cache_file)


# -----------------------------------------------------------
# MANEJO INTELIGENTE DE SITEMAPS
# -----------------------------------------------------------
def process_sitemaps(name, domain):
    # Probar sitemap.xml
    if download(urljoin(domain + "/", "sitemap.xml")):
        check_and_diff(name, domain, "sitemap.xml")
        return

    # Probar sitemap_index.xml (WP, Shopify)
    if download(urljoin(domain + "/", "sitemap_index.xml")):
        check_and_diff(name, domain, "sitemap_index.xml")
        return

    print(f"  ⚠ No se encontró sitemap válido en {domain}")


# -----------------------------------------------------------
# MAIN
# -----------------------------------------------------------
def main():
    with open("data/sites.json", "r", encoding="utf-8") as f:
        sites = json.load(f)

    for site in sites:
        name = site["name"]
        domain = site["domain"]

        download(domain)  # test inicial: valida status code general

        check_and_diff(name, domain, "robots.txt")
        process_sitemaps(name, domain)


if __name__ == "__main__":
    main()
