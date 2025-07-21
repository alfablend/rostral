from bs4 import BeautifulSoup
import typer
from urllib.parse import urljoin
from .base import PipelineStage
from rostral.models import ExtractFieldConfig
from rostral.stages.transforms import TRANSFORM_REGISTRY
from rostral.db import is_known_by_hash, get_event_hash

class ExtractStage(PipelineStage):
    """
    Parses HTML, selects elements and builds records
    according to the template’s `fields` mapping.
    """

    def run(self, data):
        seen_urls = set()
        html_input = data.get("html") or data.get("xml")
        typer.echo(f"🔬 Превью входного текста:\n{html_input[:500]}")

        if not html_input: 
            typer.echo("⚠️ ExtractStage: no HTML or XML found in input")
            return {}

        source_type = self.config.source.type
        parser_type = "html.parser" if source_type == "html" else "xml"
        soup = BeautifulSoup(html_input, parser_type)
        base_url = self.config.source.url

        result = {}

        for block_name, block_cfg in (self.config.extract or {}).items():
            typer.echo(f"🔍 ExtractStage: processing block '{block_name}' (selector='{block_cfg.selector}')")
            elements = soup.select(block_cfg.selector)
            if block_cfg.limit:
                elements = elements[:block_cfg.limit]
            typer.echo(f"   ➤ Found {len(elements)} elements, limit={block_cfg.limit or 'None'}")

            items = []
            for el in elements:
                record = {}

                for field_name, rule in block_cfg.fields.items():
                    try:
                        if isinstance(rule, str) and rule == "self":
                            value = el.get_text(strip=True)

                        elif isinstance(rule, ExtractFieldConfig):
                            raw = el.get(rule.attr, "").strip()
                            value = raw

                            if rule.transform:
                                typer.echo(f"   🧪 Jinja2 transform on '{field_name}'")
                                value = self.render_transform(rule.transform, raw)

                            if rule.transform_type:
                                fn = TRANSFORM_REGISTRY.get(rule.transform_type)
                                typer.echo(f"   🔧 Applying transform_type='{rule.transform_type}' to '{raw}'")
                                value = fn(raw, template_name=self.config.template_name, base_url=base_url)

                        else:
                            typer.echo(f"⚠️ Unsupported rule type for field '{field_name}'")
                            value = ""

                        record[field_name] = value

                    except Exception as e:
                        typer.echo(f"❌ Error extracting field '{field_name}': {e}")
                        record[field_name] = ""

                # ⛓️ Обогащение и фильтрация после извлечения всех полей
                full_url = urljoin(base_url, record.get("url", ""))
                record["url_final"] = full_url

                if not record.get("title"):
                    typer.echo(f"⏭️ Пропуск записи без title → {full_url}")
                    continue


                if full_url in seen_urls:
                    typer.echo(f"⏭️ Повторный URL в HTML → {full_url}")
                    continue

                seen_urls.add(full_url)
                items.append(record)
                typer.echo(f"   📄 Record: {record}")

            typer.echo(f"📦 Уникальных новых записей: {len(items)}")
            result[block_name] = items

        return result
