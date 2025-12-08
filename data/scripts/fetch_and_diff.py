import requests
import os
import json
from urllib.parse import urlparse

OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

COMMON_SITEMAP_PATHS = [
    "/sitemap.xml",
    "/sitemap_index.xml",
    "/sitemap/sitemap.xml",
    "/sitemap1.xml",
    "/sitemap-index.xml",
    "/sitemap-main.xml"
]

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; SEO-Monitor/1.0)"}

def safe_fetch(url, timeout=12):
    """Realiza la request con retries y manejo de errores."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        if r.status_code == 200:
            return r.text
        return None
    except Exception:
        return None

def clean_domain(url):
    """
    De https://xubio.com/ar → xubio.com
    De https://www.site.com → site.com
    """
    parsed = urlparse(url)
    host = parsed.netloc
    if host.startswith("www."):
        host = host[4:]
    # Quitar paths como /ar
    return host

def find_sitemap_in_robots(robots_text):
    sitemaps = []
    for line in robots_text.splitlines():
        line = line.strip().lower()
        if line.startswith("sitemap:"):
            sitemaps.append(line.split(":", 1)[1].strip())
    return sitemaps

def discover_for_site(site):
    name = site["name"]
    original_domain = site["domain"]

    domain = clean_domain(original_domain)

    print(f"\n🔍 {name} ({domain})")

    robots_url = f"https://{domain}/robots.txt"
    print(f" → Robots: {robots_url}")

    robots_content = safe_fetch(robots_url)

    discovered = {
        "name": name,
        "domain": domain,
        "robots_url": robots_url,
        "robots_content": robots_content,
        "sitemaps": []
    }

    # 1) buscar sitemaps declarados en robots
    if robots_content:
        declared = find_sitemap_in_robots(robots_content)
        discovered["sitemaps"].extend(declared)

    # 2) si no hay sitemap declarado, probar rutas comunes
    if len(discovered["sitemaps"]) == 0:
        for path in COMMON_SITEMAP_PATHS:
            test_url = f"https://{domain}{path}"
            content = safe_fetch(test_url)
            if content:
                discovered["sitemaps"].append(test_url)
                break

    # 3) descargar contenido real de cada sitemap detectado
    sitemap_contents = {}
    for sm_url in discovered["sitemaps"]:
        print(f" → Sitemap: {sm_url}")
        content = safe_fetch(sm_url)
        if content:
            sitemap_contents[sm_url] = content

    discovered["sitemap_contents"] = sitemap_contents
    return discovered

def load_previous(filepath):
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def save_json(filepath, data):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def main():
    sites_file = "data/sites.json"

    if not os.path.exists(sites_file):
        print("❌ ERROR: No se encontró data/sites.json")
        return

    with open(sites_file, "r", encoding="utf-8") as f:
        sites = json.load(f)

    for site in sites:
        data = discover_for_site(site)

        output_file = os.path.join(OUTPUT_DIR, f"{data['domain']}.json")
        previous = load_previous(output_file)

        if previous != data:
            print(f"🟢 Cambios detectados → guardando {data['domain']}")
            save_json(output_file, data)
        else:
            print(f"⚪ Sin cambios en {data['domain']}")

if __name__ == "__main__":
    main()
