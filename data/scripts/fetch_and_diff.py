import requests
import os
import json
import difflib
from urllib.parse import urlparse

OUTPUT_DIR = "output"
DIFF_DIR = "difs"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(DIFF_DIR, exist_ok=True)

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
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        if r.status_code == 200:
            return r.text
        return None
    except Exception:
        return None


def clean_domain(url):
    parsed = urlparse(url)
    host = parsed.netloc
    if host.startswith("www."):
        host = host[4:]
    return host


def find_sitemap_in_robots(robots_text):
    sitemaps = []
    for line in robots_text.splitlines():
        line = line.strip()
        if line.lower().startswith("sitemap:"):
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
        "robots_content": robots_content or "",
        "sitemaps": []
    }

    if robots_content:
        discovered["sitemaps"].extend(find_sitemap_in_robots(robots_content))

    if len(discovered["sitemaps"]) == 0:
        for path in COMMON_SITEMAP_PATHS:
            test_url = f"https://{domain}{path}"
            content = safe_fetch(test_url)
            if content:
                discovered["sitemaps"].append(test_url)
                break

    sitemap_contents = {}
    for sm_url in discovered["sitemaps"]:
        print(f" → Sitemap: {sm_url}")
        c = safe_fetch(sm_url)
        if c:
            sitemap_contents[sm_url] = c

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


def diff_html(title, old, new):
    diff = difflib.HtmlDiff(wrapcolumn=80).make_table(
        old.splitlines(),
        new.splitlines(),
        "Antes",
        "Ahora",
        context=True,
        numlines=3
    )

    return f"""
    <h2>{title}</h2>
    {diff}
    <hr>
    """


def generate_full_html(domain, prev, curr):
    css = """
    <style>
    body { font-family: Arial, sans-serif; padding: 20px; }
    h1 { margin-bottom: 20px; }
    table.diff { font-size: 14px; border: 1px solid #ccc; border-collapse: collapse; }
    .diff_header { background: #eee; }
    .diff_add { background: #e6ffe6; }  /* verde */
    .diff_sub { background: #ffe6e6; }  /* rojo */
    .diff_chg { background: #ffffcc; }  /* amarillo */
    </style>
    """

    html = f"<html><head>{css}</head><body>"
    html += f"<h1>Cambios detectados en {domain}</h1>"

    # Robots
    html += diff_html("robots.txt", prev.get("robots_content", ""), curr.get("robots_content", ""))

    # Cada sitemap en su sección
    prev_s = prev.get("sitemap_contents", {})
    curr_s = curr.get("sitemap_contents", {})

    all_keys = sorted(set(prev_s.keys()) | set(curr_s.keys()))

    for url in all_keys:
        old_val = prev_s.get(url, "")
        new_val = curr_s.get(url, "")

        html += diff_html(f"Sitemap: {url}", old_val, new_val)

    html += "</body></html>"

    return html


def main():
    sites_file = "data/sites.json"

    if not os.path.exists(sites_file):
        print("❌ ERROR: No se encontró data/sites.json")
        return

    with open(sites_file, "r", encoding="utf-8") as f:
        sites = json.load(f)

    for site in sites:
        current = discover_for_site(site)

        output_file = os.path.join(OUTPUT_DIR, f"{current['domain']}.json")
        previous = load_previous(output_file)

        if previous != current:
            print(f"🟢 Cambios detectados → guardando {current['domain']}")
            save_json(output_file, current)

            # generar HTML diff
            diff_file = os.path.join(DIFF_DIR, f"{current['domain']}.html")
            html = generate_full_html(current["domain"], previous or {}, current)
            with open(diff_file, "w", encoding="utf-8") as f:
                f.write(html)

        else:
            print(f"⚪ Sin cambios en {current['domain']}")


if __name__ == "__main__":
    main()
