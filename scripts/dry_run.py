import sys, yaml, requests
from bs4 import BeautifulSoup
from jinja2 import Template

# Loads a YAML template from the specified file path
def load_template(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)

# Fetches raw HTML from the test_event URL
def get_html(url):
    print(f"🔗 Fetching: {url}")
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    return r.text

# Extracts fields from the HTML using CSS selectors defined in the template
def extract_fields(html, extract_conf):
    soup = BeautifulSoup(html, "html.parser")
    result = {}
    for key, selector in extract_conf.items():
        # Supports attribute selection, e.g., a[href]::attr(href)
        if "::attr(" in selector:
            base, attr = selector.split("::attr(")
            attr = attr.rstrip(")")
            el = soup.select_one(base.strip())
            result[key] = el[attr].strip() if el and attr in el.attrs else None
        else:
            el = soup.select_one(selector)
            result[key] = el.text.strip() if el else None
    return result

# Renders the alert title and text using the extracted fields
def render_alert(alert_conf, data):
    title_tpl = Template(alert_conf["title"])
    text_tpl = Template(alert_conf["text"])
    return title_tpl.render(**data), text_tpl.render(**data)

# Entrypoint: requires one argument (path to the YAML template)
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python dry_run.py path/to/template.yaml")
        sys.exit(1)

    # Load the YAML template
    tpl = load_template(sys.argv[1])

    # Ensure test_event.url exists in the template
    test_url = tpl.get("test_event", {}).get("url")
    if not test_url:
        print("❌ test_event.url not found")
        sys.exit(1)

    # Fetch HTML and extract fields
    html = get_html(test_url)
    extracted = extract_fields(html, tpl["extract"])

    # Display extracted results
    print("\n🔎 Extracted:")
    for k, v in extracted.items():
        print(f"  {k}: {v}")

    # Render and display the alert preview
    print("\n📣 Alert Preview:")
    title, text = render_alert(tpl["alert"], extracted)
    print(f"  Title: {title}\n  Text: {text}")
