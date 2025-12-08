import os
import json
import requests
import difflib
from datetime import datetime

DATA_DIR = "output"
DIFFS_DIR = "difs"
LOGS_DIR = "logs"
SITES_FILE = "data/scripts/sites.json"

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(DIFFS_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

def fetch_url(url):
    try:
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            return r.text
        return ""
    except:
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
    html_diff = difflib.HtmlDiff().make_file(
        before.splitlines(), after.splitlines(),
        fromdesc="Antes", todesc="Ahora"
    )
    with open(output_path, "w", encoding="utf8") as f:
        f.write(html_diff)

def generate_summary(before, after):
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
        for a in added:
            summary.append(f"   + {a}")

    if removed:
        summary.append("🔴 Líneas eliminadas:")
        for r in removed:
            summary.append(f"   - {r}")

    if not added and not removed:
        summary.append("No hubo cambios en el contenido.")

    return "\n".join(summary)


def log_change(domain, summary):
    log_path = os.path.join(LOGS_DIR, f"{domain}.txt")
    with open(log_path, "a", encoding="utf8") as f:
        f.write("\n" + "="*60 + "\n")
        f.write(f"Cambio detectado - {datetime.utcnow()} UTC\n")
        f.write(summary + "\n")

def process_site(name, domain, robots_url, sitemap_urls):
    print(f"\n🔍 {name} ({domain})")
    print(f" → Robots: {robots_url}")

    robots = fetch_url(robots_url)
    sitemaps_content = ""

    for sm in sitemap_urls:
        full = sm if sm.startswith("http") else domain + sm
        print(f" → Sitemap: {full}")
        sitemaps_content += f"\n# {full}\n" + fetch_url(full)

    current_combined = robots + "\n\n" + sitemaps_content
    previous_data = load_previous(domain)

    if previous_data:
        previous_combined = previous_data["robots"] + "\n\n" + previous_data["sitemaps"]
    else:
        previous_combined = ""

    if previous_combined == current_combined:
        print(f"⚪ Sin cambios en {domain}")
        return

    print(f"🟢 Cambios detectados → guardando {domain}")

    # Dif HTML
    diff_file = os.path.join(DIFFS_DIR, f"{domain}.html")
    generate_diff_html(previous_combined, current_combined, diff_file)

    # Resumen humano
    summary = generate_summary(previous_combined, current_combined)
    print("\n📌 Resumen de cambios:")
    print(summary)

    # Guardar resumen en logs
    log_change(domain, summary)

    # Guardar estado actual
    save_current(domain, robots, sitemaps_content)


# ---------------------------------------------------------------------

print("\n=== 🚀 INICIANDO SEO MONITOR ===")

with open(SITES_FILE, "r", encoding="utf8") as f:
    sites = json.load(f)

for site in sites:
    domain = site["domain"].replace("https://", "").replace("http://", "").replace("www.", "")
    robots_url = site["domain"].rstrip("/") + "/robots.txt"

    # Detectar si hay sitemap declarado en robots
    robots_txt = fetch_url(robots_url)
    sitemap_urls = [line.split("Sitemap: ")[1].strip()
                    for line in robots_txt.splitlines()
                    if line.lower().startswith("sitemap:")]

    # Fallback si no hay sitemap en robots
    if not sitemap_urls:
        sitemap_urls = [
            "/sitemap.xml",
            "/sitemap_index.xml"
        ]

    process_site(site["name"], domain, robots_url, sitemap_urls)

print("\n=== ✅ FIN DEL MONITOR ===\n")
