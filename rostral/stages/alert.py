from colorama import Fore, Style
from datetime import datetime
from jinja2 import Template
from typing import Dict, Any
from .base import PipelineStage

class AlertStage(PipelineStage):
    def run(self, data: Dict[str, Any]) -> Dict[str, Any]:
        print(f"\n{Fore.YELLOW}⏳ Запуск AlertStage{Style.RESET_ALL}")
        
        if not hasattr(self.config, 'alert'):
            print(f"{Fore.RED}⚠️ Конфигурация алертов отсутствует{Style.RESET_ALL}")
            return {"alert": {"error": "No alert config"}}

        # Объединяем GPT-ответы с основными данными
        if 'gpt_responses' in data:
            for block_name in ['events', 'documents', 'items']:
                if block_name in data and isinstance(data[block_name], list):
                    for i, item in enumerate(data[block_name]):
                        if isinstance(item, dict):
                            doc_id = f"{block_name}_{i}"
                            item['gpt'] = data['gpt_responses'].get(doc_id, {})

        # Рендерим алерты
        rendered_alerts = {}
        for template_name, template_str in self.config.alert.templates.items():
            try:
                context = {
                    'now': datetime.now(),
                    **data
                }
                template = Template(template_str)
                rendered = template.render(**context)
                rendered_alerts[template_name] = rendered
                
                # Красивый вывод в консоль
                self._print_alert(rendered, template_name)
                
            except Exception as e:
                error_msg = f"Ошибка рендеринга '{template_name}': {str(e)}"
                rendered_alerts[template_name] = error_msg
                print(f"{Fore.RED}❌ {error_msg}{Style.RESET_ALL}")

        print(f"{Fore.GREEN}✅ AlertStage завершен{Style.RESET_ALL}")
        return {"alert": rendered_alerts}

    def _print_alert(self, content: str, alert_name: str):
        """Форматированный вывод алерта в консоль"""
        print(f"\n{Fore.CYAN}🔔 {alert_name.upper()} {Style.RESET_ALL}")
        print(f"{Fore.BLUE}{'-'*50}{Style.RESET_ALL}")
        
        # Разбиваем на строки и выводим с отступами
        for line in content.split('\n'):
            if line.strip():  # Пропускаем пустые строки
                if line.startswith('==='):
                    print(f"{Fore.YELLOW}{line}{Style.RESET_ALL}")
                elif any(line.lstrip().startswith(x) for x in ['-', '•', '*']):
                    print(f"  {Fore.GREEN}{line.lstrip()}{Style.RESET_ALL}")
                elif ':' in line:
                    key, val = line.split(':', 1)
                    print(f"{Fore.MAGENTA}{key}:{Style.RESET_ALL}{val}")
                else:
                    print(line)
        
        print(f"{Fore.BLUE}{'-'*50}{Style.RESET_ALL}")