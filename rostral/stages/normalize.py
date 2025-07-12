from .base import PipelineStage
import typer
from ast import literal_eval

class NormalizeStage(PipelineStage):
    """
    Улучшенная версия NormalizeStage с:
    - Безопасным eval
    - Подробным логированием
    - Сохранением метаданных
    - Обработкой ошибок на уровне элементов
    """

    def run(self, extracted):
        typer.echo(f"⏳ NormalizeStage input keys: {list(extracted.keys())}")

        if not extracted or not hasattr(self.config, 'normalize') or not self.config.normalize.rules:
            typer.echo("ℹ️ No normalize rules defined, skipping normalization")
            return extracted

        normalized = {}
        meta = {"filter_stats": {}}

        for rule in self.config.normalize.rules:
            block_name = rule.field
            items = extracted.get(block_name, [])
            
            typer.echo(f"\n🔍 Normalizing field '{block_name}' with {len(items)} items")
            if items:
                typer.echo(f"   🧪 Пример элемента до фильтрации: {self._sample_item(items[0])}")

            filtered = items
            rule_stats = []
            
            for i, filter_rule in enumerate(rule.filters):
                temp_filtered = []
                seen = set()
                removed_count = 0
                
                for item in filtered:
                    try:
                        if not self._apply_filter(item, filter_rule):
                            removed_count += 1
                            continue
                        temp_filtered.append(item)
                    except Exception as e:
                        typer.echo(f"⚠️ Filter error on item: {e}")
                        continue

                rule_stats.append((filter_rule, removed_count))
                typer.echo(f"   🔧 Filter #{i+1}: kept {len(temp_filtered)}, removed {removed_count}")
                filtered = temp_filtered

            normalized[block_name] = filtered
            meta["filter_stats"][block_name] = {
                "initial": len(items),
                "final": len(filtered),
                "rules": [str(r) for r in rule.filters]
            }
            
            if filtered:
                typer.echo(f"   🧪 Пример элемента после фильтрации: {self._sample_item(filtered[0])}")
            typer.echo(f"✅ Final count for '{block_name}': {len(filtered)}")

        extracted["normalized"] = normalized
        extracted["__normalize_meta__"] = meta
        typer.echo("\n📊 Normalization summary:")
        for block, stats in meta["filter_stats"].items():
            typer.echo(f"  - {block}: {stats['initial']} → {stats['final']} items")
        
        return extracted

    def _sample_item(self, item):
        """Возвращает упрощенное представление элемента для логов"""
        return {k: v for k, v in item.items() 
                if not isinstance(v, (bytes, dict))}

    def _apply_filter(self, item, filter_rule):
        """Применяет все фильтры к элементу"""
        # Unique filter
        if hasattr(filter_rule, 'unique'):
            key = item.get(filter_rule.unique)
            if key in getattr(self, '_seen_unique', set()):
                return False
            self._seen_unique.add(key)
        
        # Condition filter
        if hasattr(filter_rule, 'condition'):
            if not self._safe_eval(filter_rule.condition, {"item": item}):
                return False
                
        return True

    def _safe_eval(self, condition: str, context: dict) -> bool:
        """Безопасное выполнение условий"""
        try:
            return bool(literal_eval(condition, context))
        except:
            return False