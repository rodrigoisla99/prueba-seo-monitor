import os
import json
import requests
import difflib
import re
from datetime import datetime

# Lista global de cambios detectados en esta ejecución
RUN_CHANGES = []

# -------------------------------------------------
# RUTAS BASADAS EN LA UBICACIÓN DEL SCRIPT
# -------------------------------------------------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))      # .../data/scripts
REPO_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))     # raíz del repo

DATA_DIR = os.path.join(REPO_ROOT, "output")
DIFFS_DIR = os.path.join(REPO_ROOT, "diffs")
LOGS_DIR = os.path.join(REPO_ROOT, "logs")
SITES_FILE = os.path.join(REPO_ROOT, "data", "sites.json")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(DIFFS_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

# -------------------------------------------------
# IGNORAR CAMBIOS NO REALES (lastmod)
# -------------------------------------------------

def remove_lastmod_dates(text):
    """
    Elimina <lastmod>AAAA-MM-DD</lastmod> del contenido.
    Así evitamos alertas por regeneración automática diaria del sitemap.
    """
    text = re.sub(r"<lastmod>\d{4}-\d{2}-\d{2}</lastmod>", "", text)
    text = re.sub(r"\s+", " ", text)  # Limpieza opcional
    return text.strip()

# -------------------------------------------------
# FUNCIONES AUXILIARES
# -------------------------------------------------

def fetch_url(url):
    """Descarga una URL y devuelve el texto, o cadena vacía si falla."""
    try:
        r = requests.get(url, timeout=20)
        if r.status_code == 200:
            return r.text
        print(f"⚠ {url} devolvió status {r.status_code}")
        return ""
    except Exception as e:
        print(f"⚠ Error al descargar {url}: {e}")
        return ""

def sanitize_domain_key(domain):
    """
    Genera una key segura para usar en nombres de archivo.
    Ej: https://xubio.com/ar -> xubio.com_ar
    """
    base = (
        domain.rstrip("/")
        .replace("https://", "")
        .replace("http://", "")
        .replace("www.", "")
    )
    return base.replace("/", "_")

def load_previous(domain_key):
    """Carga el JSON previo para un dominio (si existe)."""
    file = os.path.join(DATA_DIR, f"{domain_key}.json")
    if not os.path.exists(file):
        return None
    with open(file, "r", encoding="utf8") as f:
        return json.load(f)

def save_current(domain_key, robots, sitemaps):
    """Guarda el estado actual (robots + sitemaps) para el dominio."""
    file = os.path.join(DATA_DIR, f"{domain_key}.json")
    with open(file, "w", encoding="utf8") as f:
        json.dump({"robots": robots, "sitemaps": sitemaps}, f, indent=2)

def normalize_old_data(value):
    """
    Normaliza datos viejos que pueden venir como lista/dict.
    """
    if isinstance(value, list):
        return "\n".join(str(v) for v in value)
    if isinstance(value, dict):
        return json.dumps(value, indent=2, ensure_ascii=False)
    if isinstance(value, str):
        return value
    return str(value)

def normalize_sitemap_url(raw_sm, base_url):
    """Normaliza rutas de sitemaps a URLs absolutas."""
    if not raw_sm:
        return None
    sm = raw_sm.strip()
    if not sm:
        return None
    if sm.startswith("http://") or sm.startswith("https://"):
        return sm
    if sm.startswith("//"):
        return "https:" + sm
    if sm.startswith("/"):
        return base_url + sm
    return "https://" + sm.lstrip("/")

def save_versions_plain(domain_key, before, after):
    """Guarda versión anterior y nueva en TXT para verlo fácil."""
    before_path = os.path.join(DIFFS_DIR, f"{domain_key}_before.txt")
    after_path = os.path.join(DIFFS_DIR, f"{domain_key}_after.txt")

    with open(before_path, "w", encoding="utf8") as f:
        f.write(before)

    with open(after_path, "w", encoding="utf8") as f:
        f.write(after)

def generate_summary(before, after, max_lines=40):
    """Genera un resumen humano del diff."""
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
    if removed:
        summary.append("🔴 Líneas eliminadas:")
        for r in removed[:max_lines]:
            summary.append(f"   - {r}")
    if not added and not removed:
        summary.append("No hubo cambios en el contenido.")

    return "\n".join(summary)

def log_change(domain_key, summary):
    """Guarda el resumen en logs."""
    log_path = os.path.join(LOGS_DIR, f"{domain_key}.txt")
    with open(log_path, "a", encoding="utf8") as f:
        f.write("\n" + "=" * 60 + "\n")
        f.write(f"Cambio detectado - {datetime.utcnow()} UTC\n")
        f.write(summary + "\n")

def build_combined_content(robots, sitemaps):
    """Arma un bloque unificado para comparar."""
    return (
        "### ROBOTS.TXT ###\n"
        + (robots or "")
        + "\n\n### SITEMAPS ###\n"
        + (sitemaps or "")
    )

def extract_sitemaps_from_robots(robots_txt):
    """Detecta líneas Sitemap: en robots.txt."""
    sitemaps = []
    for line in robots_txt.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.lower().startswith("sitemap:"):
            value = stripped.split(":", 1)[1].strip()
            if value:
                sitemaps.append(value)
    return sitemaps

# -------------------------------------------------
# PROCESAR CADA SITIO
# -------------------------------------------------

def process_site(name, domain):
    base_url = domain.rstrip("/")
    domain_key = sanitize_domain_key(domain)

    robots_url = base_url + "/robots.txt"

    print(f"\n🔍 {name} ({domain_key})")
    print(f" → Robots: {robots_url}")

    robots_txt = fetch_url(robots_url)

    raw_sitemaps = extract_sitemaps_from_robots(robots_txt)
    if not raw_sitemaps:
        raw_sitemaps = ["/sitemap.xml", "/sitemap_index.xml"]

    sitemap_urls = []
    for sm in raw_sitemaps:
        norm = normalize_sitemap_url(sm, base_url)
        if norm:
            sitemap_urls.append(norm)

    sitemaps_content = ""
    for sm_url in sitemap_urls:
        print(f" → Sitemap: {sm_url}")
        sitemaps_content += f"\n# {sm_url}\n"
        sitemaps_content += fetch_url(sm_url)

    current_combined = build_combined_content(robots_txt, sitemaps_content)

    previous_data = load_previous(domain_key)

    if previous_data is None:
        print(f"🟡 Primera ejecución para {domain_key}: guardando baseline.")
        save_current(domain_key, robots_txt, sitemaps_content)
        return

    prev_robots = normalize_old_data(previous_data.get("robots", ""))
    prev_sitemaps = normalize_old_data(previous_data.get("sitemaps", ""))
    previous_combined = build_combined_content(prev_robots, prev_sitemaps)

    # -------------------------------------------------
    # 🔥 NUEVA COMPARACIÓN QUE IGNORA CAMBIOS EN <lastmod>
    # -------------------------------------------------

    clean_prev = remove_lastmod_dates(previous_combined)
    clean_curr = remove_lastmod_dates(current_combined)

    if clean_prev == clean_curr:
        print(f"⚪ Sin cambios reales en {domain_key} (solo lastmod actualizado)")
        return

    # -------------------------------------------------

    print(f"🟢 Cambios detectados en {domain_key} → generando resumen y versiones")

    save_versions_plain(domain_key, previous_combined, current_combined)

    summary = generate_summary(previous_combined, current_combined)
    print("\n📌 Resumen de cambios:")
    print(summary)

    log_change(domain_key, summary)

    short_header = f"[{datetime.utcnow()} UTC] {name} ({domain_key})"
    RUN_CHANGES.append(short_header + "\n" + summary)

    save_current(domain_key, robots_txt, sitemaps_content)

# -------------------------------------------------
# EJECUCIÓN PRINCIPAL
# -------------------------------------------------

print("\n=== 🚀 INICIANDO SEO MONITOR ===")

if not os.path.exists(SITES_FILE):
    raise FileNotFoundError(f"No se encontró el archivo de sitios: {SITES_FILE}")

with open(SITES_FILE, "r", encoding="utf8") as f:
    sites = json.load(f)

for site in sites:
    process_site(site["name"], site["domain"])

last_run_path = os.path.join(LOGS_DIR, "_last_run.txt")
with open(last_run_path, "w", encoding="utf8") as f:
    f.write(f"Resumen de cambios - {datetime.utcnow()} UTC\n")
    f.write("=" * 60 + "\n\n")
    if not RUN_CHANGES:
        f.write("No se detectaron cambios en ningún sitio.\n")
    else:
        for block in RUN_CHANGES:
            f.write(block)
            f.write("\n\n" + "-" * 40 + "\n\n")

print("\n=== ✅ FIN DEL MONITOR ===\n")
