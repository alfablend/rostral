# rostral/stages/json_extract.py

import json
import typer
import jmespath
from typing import Any
from .base import PipelineStage
from rostral.models import ExtractFieldConfig
from rostral.stages.transforms import TRANSFORM_REGISTRY

class JsonExtractStage(PipelineStage):
    """
    Стадия для извлечения данных из JSON с использованием JMESPath
    """
    
    def run(self, data: dict) -> dict:
        json_data = data.get("json")
        
        if not json_data:
            typer.echo("⚠️ JsonExtractStage: входные данные не содержат JSON")
            return {}
            
        typer.echo(f"🔍 JsonExtractStage: обработка JSON (тип: {type(json_data)})")
        
        result = {}
        
        for block_name, block_cfg in (self.config.extract or {}).items():
            try:
                selector = block_cfg.selector.lstrip('$.')
                items = jmespath.search(selector, json_data) or []
                
                if not isinstance(items, list):
                    items = [items]
                    
                processed_items = []
                
                for item in items:
                    if not item:
                        continue
                        
                    record = self._process_item(item, block_cfg)
                    if record:
                        processed_items.append(record)
                
                result[block_name] = processed_items
                
            except Exception as e:
                typer.echo(f"❌ Ошибка в блоке {block_name}: {str(e)}")
                result[block_name] = []
        
        return result
    
    def _process_item(self, item: dict, block_cfg: Any) -> dict:
        
        debug_info = {
            'item_keys': list(item.keys()),
            'sample_data': {k: item.get(k) for k in list(item.keys())[:3]},
            'jmespath_guid': jmespath.search('guid', item)
        }   
        typer.echo(f"\n🔍 Debug: {json.dumps(debug_info, indent=2)}")
        
        record = {}
        context = {}

        # 1. Собираем все поля согласно конфигу
        for field_name, rule in block_cfg.fields.items():
            try:
                if isinstance(rule, str):
                    # Простые JMESPath выражения
                    value = jmespath.search(rule.lstrip('$.'), item)
                    record[field_name] = value if value is not None else ""
                    context[field_name] = record[field_name]
                
                elif isinstance(rule, ExtractFieldConfig):
                    # Сложные поля с трансформациями
                    raw_value = jmespath.search(rule.attr.lstrip('$.'), item) if rule.attr else None
                    
                    if rule.transform_type == 'jinja':
                        context['value'] = raw_value
                        rendered = TRANSFORM_REGISTRY['jinja'](
                            template_str=rule.transform,
                            context=context
                        )
                        record[field_name] = rendered
                        context[field_name] = rendered

            except Exception as e:
                typer.echo(f"❌ {field_name}: {str(e)}", err=True)
                record[field_name] = ""

        return record