import sys, yaml, requests
from bs4 import BeautifulSoup
from jinja2 import Template

# Load YAML template from file
def load_template(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)

# Download HTML content from the test_event.url
def get_html(url):
    print(f"🔗 Fetching: {url}")
    headers = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br"
    }
    r = requests.get(url, headers=headers, timeout=10)
    r.raise_for_status()
    with open("debug_output.html", "w", encoding="utf-8") as f:
        f.write(r.text)
    return r.text

# Apply CSS selectors from the extract block to parse HTML
def extract_fields(html, extract_conf):
    soup = BeautifulSoup(html, "html.parser")
    result = {}
    for key, selector in extract_conf.items():
        # Support for attribute selectors like "a::attr(href)"
        if "::attr(" in selector:
            base, attr = selector.split("::attr(")
            attr = attr.rstrip(")")
            el = soup.select_one(base.strip())
            result[key] = el[attr].strip() if el and attr in el.attrs else None
        else:
            el = soup.select_one(selector)
            result[key] = el.text.strip() if el else None
    return result

# Normalize extracted fields based on normalize block
# If passthrough is enabled, copy extract.* → normalized.*
def normalize_fields(extracted, normalize_conf):
    if normalize_conf.get("passthrough"):
        return extracted
    fields = normalize_conf.get("fields", {})
    result = {}
    for key in fields:
        # Stub: just copy from extract for now
        result[key] = extracted.get(key)
    return result

# Simulate GPT summary generation (placeholder)
def generate_gpt_summary():
    return "This is a placeholder summary generated by GPT. Replace with real model output."

# Render alert.template using normalized fields and GPT summary
def render_alert(alert_conf, normalized, gpt_summary):
    if "template" not in alert_conf:
        raise ValueError("❌ Missing alert.template in YAML")
    tpl = Template(alert_conf["template"])
    return tpl.render(
        normalized=normalized,
        gpt_summary=gpt_summary,
        document_link=normalized.get("document")
    )

# Entry point: load template, fetch test URL, extract → normalize → render
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python dry_run.py path/to/template.yaml")
        sys.exit(1)

    tpl = load_template(sys.argv[1])
    test_url = tpl.get("test_event", {}).get("url")
    if not test_url:
        print("❌ test_event.url not found")
        sys.exit(1)

    html = get_html(test_url)
    extracted = extract_fields(html, tpl["extract"])
    normalized = normalize_fields(extracted, tpl.get("normalize", {}))
    gpt_summary = generate_gpt_summary()

    print("\n🔎 Extracted:")
    for k, v in extracted.items():
        print(f"  {k}: {v}")

    print("\n🧠 Normalized:")
    for k, v in normalized.items():
        print(f"  {k}: {v}")

    print("\n📣 Alert Preview:")
    alert_text = render_alert(tpl["alert"], normalized, gpt_summary)
    print(alert_text)
