import os
import json
import requests
import difflib
from datetime import datetime

# -------------------------------------------------
# RUTAS BASADAS EN LA UBICACIÓN DEL SCRIPT
# -------------------------------------------------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))      # .../data/scripts
REPO_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))     # raíz del repo

DATA_DIR = os.path.join(REPO_ROOT, "output")
DIFFS_DIR = os.path.join(REPO_ROOT, "difs")
LOGS_DIR = os.path.join(REPO_ROOT, "logs")
SITES_FILE = os.path.join(SCRIPT_DIR, "sites.json")          # siempre al lado del script

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(DIFFS_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)


# -------------------------------------------------
# FUNCIONES AUXILIARES
# -------------------------------------------------

def fetch_url(url):
    try:
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            return r.text
        return ""
    except Exception as e:
        print(f"⚠ Error al descargar {url}: {e}")
        return ""


def load_previous(domain):
    file = os.path.join(DATA_DIR, f"{domain}.json")
    if not os.path.exists(file):
        return None
    with open(file, "r", encoding="utf8") as f:
        return json.load(f)


def save_current(domain, robots, sitemaps):
    file = os.path.join(DATA_DIR, f"{domain}.json")
    with open(file, "w", encoding="utf8") as f:
        json.dump({"robots": robots, "sitemaps": sitemaps}, f, indent=2)


def generate_diff_html(before, after, output_path):
    """
    Genera un diff HTML más legible, con contexto en torno a los cambios.
    """
    diff = difflib.HtmlDiff(wrapcolumn=80)
    html_diff = diff.make_file(
        before.splitlines(),
        after.splitlines(),
        fromdesc="Versión anterior",
        todesc="Versión nueva",
        context=True,      # solo alrededor de los cambios
        numlines=5         # 5 líneas de contexto
    )
    with open(output_path, "w", encoding="utf8") as f:
        f.write(html_diff)


def generate_summary(before, after, max_lines=30):
    """
    Devuelve un resumen en texto simple:
    - líneas agregadas
    - líneas eliminadas
    Limitado a max_lines para que no se vuelva inmanejable.
    """
    before_lines = before.splitlines()
    after_lines = after.splitlines()

    diff = difflib.unified_diff(before_lines, after_lines, lineterm="")

    added = []
    removed = []

    for line in diff:
        if line.startswith("+") and not line.startswith("+++"):
            added.append(line[1:])
        elif line.startswith("-") and not line.startswith("---"):
            removed.append(line[1:])

    summary = []

    if added:
        summary.append("🟢 Líneas agregadas:")
        for a in added[:max_lines]:
            summary.append(f"   + {a}")
        if len(added) > max_lines:
            summary.append(f"   ... (+{len(added) - max_lines} líneas más agregadas)")

    if removed:
        summary.append("🔴 Líneas eliminadas:")
        for r in removed[:max_lines]:
            summary.append(f"   - {r}")
        if len(removed) > max_lines:
            summary.append(f"   ... (-{len(removed) - max_lines} líneas más eliminadas)")

    if not added and not removed:
        summary.append("No hubo cambios en el contenido.")

    return "\n".join(summary)


def log_change(domain, summary):
    log_path = os.path.join(LOGS_DIR, f"{domain}.txt")
    with open(log_path, "a", encoding="utf8") as f:
        f.write("\n" + "=" * 60 + "\n")
        f.write(f"Cambio detectado - {datetime.utcnow()} UTC\n")
        f.write(summary + "\n")


def save_versions_plain(domain, before, after):
    """
    Guarda versión anterior y nueva en TXT para verlo fácil.
    """
    before_path = os.path.join(DIFFS_DIR, f"{domain}_before.txt")
    after_path = os.path.join(DIFFS_DIR, f"{domain}_after.txt")

    with open(before_path, "w", encoding="utf8") as f:
        f.write(before)

    with open(after_path, "w", encoding="utf8") as f:
        f.write(after)


def process_site(name, domain, robots_url, sitemap_urls):
    print(f"\n🔍 {name} ({domain})")
    print(f" → Robots: {robots_url}")

    # Contenido actual
    robots = fetch_url(robots_url)
    sitemaps_content = ""

    for sm in sitemap_urls:
        full = sm if sm.startswith("http") else domain + sm
        print(f" → Sitemap: {full}")
        sitemaps_content += f"\n# {full}\n" + fetch_url(full)

    current_combined = robots + "\n\n" + sitemaps_content

    # Cargar versión anterior (si existe)
    previous_data = load_previous(domain)

    # Primera vez: guardamos baseline y salimos
    if previous_data is None:
        print(f"🟡 Primera ejecución para {domain}: guardando baseline.")
        save_current(domain, robots, sitemaps_content)
        return

    previous_combined = previous_data.get("robots", "") + "\n\n" + previous_data.get("sitemaps", "")

    # Comparar
    if previous_combined == current_combined:
        print(f"⚪ Sin cambios en {domain}")
        return

    print(f"🟢 Cambios detectados en {domain} → generando diffs")

    # Guardar versiones plana (before/after)
    save_versions_plain(domain, previous_combined, current_combined)

    # Dif HTML
    diff_file = os.path.join(DIFFS_DIR, f"{domain}.html")
    generate_diff_html(previous_combined, current_combined, diff_file)

    # Resumen humano
    summary = generate_summary(previous_combined, current_combined)
    print("\n📌 Resumen de cambios:")
    print(summary)

    # Guardar resumen en logs
    log_change(domain, summary)

    # Guardar estado actual para la próxima ejecución
    save_current(domain, robots, sitemaps_content)


# -------------------------------------------------
# EJECUCIÓN PRINCIPAL
# -------------------------------------------------

print("\n=== 🚀 INICIANDO SEO MONITOR ===")

if not os.path.exists(SITES_FILE):
    raise FileNotFoundError(f"No se encontró el archivo de sitios: {SITES_FILE}")

with open(SITES_FILE, "r", encoding="utf8") as f:
    sites = json.load(f)

for site in sites:
    domain = site["domain"].replace("https://", "").replace("http://", "").replace("www.", "")
    robots_url = site["domain"].rstrip("/") + "/robots.txt"

    # Detectar si hay sitemap declarado en robots
    robots_txt = fetch_url(robots_url)
    sitemap_urls = [
        line.split("Sitemap: ")[1].strip()
        for line in robots_txt.splitlines()
        if line.lower().startswith("sitemap:")
    ]

    # Fallback si no hay sitemap en robots
    if not sitemap_urls:
        sitemap_urls = [
            "/sitemap.xml",
            "/sitemap_index.xml",
        ]

    process_site(site["name"], domain, robots_url, sitemap_urls)

print("\n=== ✅ FIN DEL MONITOR ===\n")

