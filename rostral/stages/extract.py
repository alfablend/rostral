from bs4 import BeautifulSoup
import typer
from .base import PipelineStage
from rostral.models import ExtractFieldConfig
from rostral.stages.transforms import TRANSFORM_REGISTRY

class ExtractStage(PipelineStage):
    """
    Parses HTML, selects elements and builds records
    according to the template’s `fields` mapping.
    """

    def run(self, data):
        html_input = data.get("html") or data.get("xml")
        typer.echo(f"🔬 Превью входного текста:\n{html_input[:500]}")

        if not html_input: 
            typer.echo("⚠️  ExtractStage: no HTML or XML found in input")
            return {}

        source_type = self.config.source.type
        parser_type = "html.parser" if source_type == "html" else "xml"
        soup = BeautifulSoup(html_input, parser_type)


        result = {}

        for block_name, block_cfg in (self.config.extract or {}).items():
            typer.echo(f"🔍 ExtractStage: processing block '{block_name}' (selector='{block_cfg.selector}')")
            limit = getattr(block_cfg, "limit", None)
            if limit is not None:
                elements = soup.select(block_cfg.selector)[:limit]
            else:
                elements = soup.select(block_cfg.selector)
            typer.echo(f"   ➤ Found {len(elements)} elements, limit={limit if limit is not None else 'None'}")

            items = []
            for el in elements:
                record = {}

                for field_name, rule in block_cfg.fields.items():
                    try:
                        # Case 1: shorthand "self"
                        if isinstance(rule, str) and rule == "self":
                            value = el.get_text(strip=True)

                        # Case 2: full ExtractFieldConfig
                        elif isinstance(rule, ExtractFieldConfig):
                            # Step 1: get raw value
                            if parser_type == "xml" and rule.attr:
                                target = el.find(rule.attr)
                                raw = target.text.strip() if target else ""
                            else:
                                raw = el.get(rule.attr, "").strip()

                            value = raw

                            # Step 2: apply Jinja2 transform
                            if rule.transform:
                                typer.echo(f"   🧪 Jinja2 transform on '{field_name}'")
                                value = self.render_transform(rule.transform, raw)

                            if rule.transform_type:
                                fn = TRANSFORM_REGISTRY.get(rule.transform_type)
                                typer.echo(f"   🔧 Applying transform_type='{rule.transform_type}' to '{raw}'")
                                value = fn(raw, template_name=self.config.template_name) if fn else raw  # Добавлен template_name

                        else:
                            typer.echo(f"⚠️  Unsupported rule type for field '{field_name}'")
                            value = ""

                        record[field_name] = value

                    except Exception as e:
                        typer.echo(f"❌ Error extracting field '{field_name}': {e}")
                        record[field_name] = ""

                typer.echo(f"   📄 Record: {record}")
                items.append(record)

            typer.echo(f"   ✔ Collected {len(items)} records for '{block_name}'")
            result[block_name] = items

        return result
