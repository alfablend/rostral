from bs4 import BeautifulSoup
import typer
from urllib.parse import urljoin
from .base import PipelineStage
from rostral.models import ExtractFieldConfig
from rostral.stages.transforms import TRANSFORM_REGISTRY
from rostral.db import is_known_by_hash, get_event_hash

class ExtractStage(PipelineStage):
    def run(self, data):
        seen_urls = set()
        html_input = data.get("html") or data.get("xml")
        
        if not html_input: 
            typer.echo("⚠️ ExtractStage: no HTML or XML found in input")
            return {}

        is_rss = self.config.source.type == "rss"
        parser_type = "lxml-xml" if is_rss else "html.parser"
        soup = BeautifulSoup(html_input, parser_type)
        base_url = self.config.source.url

        result = {}

        for block_name, block_cfg in (self.config.extract or {}).items():
            elements = soup.find_all(block_cfg.selector) if is_rss else soup.select(block_cfg.selector)
            elements = elements[:block_cfg.limit] if block_cfg.limit else elements

            items = []
            for el in elements:
                record = {}
                for field_name, rule in block_cfg.fields.items():
                    try:
                        # Существующая HTML-логика
                        if isinstance(rule, str) and rule == "self":
                            value = el.get_text(strip=True)
                        
                        elif isinstance(rule, ExtractFieldConfig):
                            if is_rss:
                                tag = el.find(rule.attr) if rule.attr else el
                                raw = tag.text.strip() if tag else ""
                            else:
                                raw = el.get(rule.attr, "").strip()
                            
                            value = raw
                            if rule.transform:
                                value = self.render_transform(rule.transform, raw)
                            if rule.transform_type:
                                fn = TRANSFORM_REGISTRY.get(rule.transform_type)
                                value = fn(raw, template_name=self.config.template_name, base_url=base_url)
                        
                        record[field_name] = value

                    except Exception as e:
                        typer.echo(f"❌ Error extracting {field_name}: {str(e)}")
                        record[field_name] = ""

                # Существующая логика обогащения
                full_url = urljoin(base_url, record.get("url", ""))
                record["url_final"] = full_url
                
                if not record.get("title"):
                    continue
                if full_url in seen_urls:
                    continue
                    
                seen_urls.add(full_url)
                items.append(record)

            result[block_name] = items
        
        return result