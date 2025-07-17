import os
import re
from pathlib import Path
from datetime import datetime
from jinja2 import Template
from .base import PipelineStage
from typing import Dict, Any, Optional

from dotenv import load_dotenv
load_dotenv()

try:
    from gpt4all import GPT4All
    gpt4all_model_path = str(Path(os.getenv("GPT4ALL_MODEL_PATH")).absolute())
    gpt4all_model_name = os.getenv("GPT4ALL_MODEL_NAME")
    gpt4all_model = GPT4All(model_name=gpt4all_model_name, model_path=gpt4all_model_path, allow_download=False) if gpt4all_model_name else None
except ImportError:
    gpt4all_model = None

try:
    import openai
    openai.api_key = os.getenv("OPENAI_API_KEY")
except ImportError:
    openai = None


class GPTStage(PipelineStage):
    """
    GPTStage рендерит prompt и отправляет его в GPT4All (по умолчанию) или OpenAI (фолбэк).
    Ответ очищается от служебных тегов и парсится в структурированный dict.
    """

    def run(self, data: Dict[str, Any]) -> Dict[str, Any]:
        print("\n" + "="*50)
        print("🚀 Запуск GPTStage для массива документов")
        print("="*50)
        
        if not hasattr(self.config, "gpt"):
            return data

        # Собираем все ответы GPT
        gpt_responses = {}
        
        # Обрабатываем все блоки-массивы
        for block_name, items in data.items():
            if not isinstance(items, list):
                continue
                
            print(f"\n🔧 Обработка блока '{block_name}' ({len(items)} документов)")
            
            for i, item in enumerate(items):
                if not isinstance(item, dict):
                    continue
                    
                print(f"\n📄 Документ #{i+1}: {item.get('title', 'Без названия')}")
                doc_id = f"{block_name}_{i}"
                
                # Получаем текст для обработки
                text = self._get_single_text(item)
                if not text:
                    gpt_responses[doc_id] = {"error": "Empty input text"}
                    continue
                    
                # Генерируем промпт и получаем ответ
                prompt = self._render_prompt(text, item)
                response = self._get_gpt_response(prompt)
                
                # Парсим и сохраняем результат
                parsed = self._parse_response(self._clean_model_output(response))
                gpt_responses[doc_id] = {
                    **parsed,
                    "_meta": {
                        "model": self._get_model_info(),
                        "prompt_length": len(prompt),
                        "response_length": len(response)
                    }
                }
                
                # Также сохраняем результат в сам документ
                item["gpt"] = gpt_responses[doc_id]
        
        return {
            **data,
            "gpt_responses": gpt_responses
        }

    def _process_single_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Обрабатывает один документ и возвращает результат"""
        text = self._get_single_text(item)
        if not text:
            return {"error": "Empty input text"}

        prompt = self._render_prompt(text, item)
        response = self._get_gpt_response(prompt)
        
        return self._parse_response(self._clean_model_output(response))

    def _get_single_text(self, item: Dict[str, Any]) -> str:
        """Получает текст для одного документа"""
        for field in ["gpt_text", "excerpt", "text"]:
            text = item.get(field)
            if text and isinstance(text, str) and text.strip():
                return text.strip()
        return ""    
    
    def _render_prompt(self, text: str, data: Dict[str, Any]) -> str:
        """Генерирует промпт с явным указанием формата ответа"""
        prompt_template = (
            self.config.gpt.prompt + 
            "\n\nТы — ассистент, который дает четкие и короткие ответы." 
            "\nНе рассуждай, просто отвечай по делу." 
            "\n\nОтвечай строго по указанному формату, без пояснений и тегов."
            "\nНе используй теги <think> или другие XML-разметки."
        )
        
        context = {
            "text": text,
            "now": datetime.now(),
            **data.get("auto_dates", {}),
            **data.get("gpt", {}),
            **data.get("normalized", {}),
        }
        
        prompt = Template(prompt_template).render(**context)
        
        print("\n🧠 Сгенерированный prompt:\n" + "-" * 40)
        print(prompt[:500] + "..." if len(prompt) > 500 else prompt)
        print("-" * 40)
        print(f"Длина prompt: {len(prompt)} символов")
        
        self._save_debug("prompt", prompt)
        return prompt

    def _get_gpt_response(self, prompt: str) -> str:
        """Получает ответ от GPT с обработкой ошибок"""
        # GPT4All
        if gpt4all_model:
            try:
                print(f"\n🚀 Используется GPT4All: {os.path.basename(gpt4all_model_path)}")
                response = ""
                
                print("📡 Потоковый ответ (сырой):")
                for chunk in gpt4all_model.generate(
                    prompt,
                    max_tokens=1024,
                    streaming=True,
                    temp=0.3, 
                    top_k=30,  
                    top_p=0.8,   
                ):
                    print(chunk, end="", flush=True)
                    response += chunk
                
                print("\n" + "-" * 40)
                return response
                
            except Exception as e:
                return {"error": f"GPT4All error: {e}"}

        # OpenAI fallback
        elif openai and os.getenv("OPENAI_API_KEY"):
            try:
                print("\n🌐 Используется OpenAI: gpt-3.5-turbo")
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[{
                        "role": "system",
                        "content": "Отвечай строго по формату без пояснений"
                    }, {
                        "role": "user",
                        "content": prompt
                    }],
                    temperature=0.3
                )
                return response.choices[0].message.content.strip()
                
            except Exception as e:
                return {"error": f"OpenAI error: {e}"}

        return {"error": "No GPT backend available"}

    def _clean_model_output(self, text: str) -> str:
        """Очищает ответ от служебных тегов и размышлений модели"""
        # Удаляем все до закрывающего тега </think> если он есть
        if '</think>' in text:
            text = text.split('</think>')[-1].strip()
        
        # Удаляем все XML-подобные теги
        text = re.sub(r'<\/?[a-z]+>', '', text)
        
        # Удаляем повторяющиеся переносы строк
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        print("\n🔧 Очищенный ответ:\n" + "-" * 40)
        print(text[:1000] + "..." if len(text) > 1000 else text)
        print("-" * 40)
        
        return text.strip()

    def _parse_response(self, text: str) -> Dict[str, str]:
        """Строгий парсинг ответа по формату ключ: значение"""
        result = {}
        current_key = None
        
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
                
            # Обрабатываем строки с разделителем ":"
            if ":" in line:
                if current_key:  # Сохраняем предыдущее значение
                    result[current_key] = result[current_key].strip()
                
                key, val = line.split(":", 1)
                current_key = key.strip().lower().replace(" ", "_")
                result[current_key] = val.strip()
            elif current_key:  # Продолжение предыдущего значения
                result[current_key] += " " + line
                
        # Удаляем технические артефакты из значений
        for key in result:
            result[key] = re.sub(r'\[\d+\]', '', result[key])
            
        return result

    def _get_text(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Возвращает словарь {doc_id: text} для всех документов"""
        texts = {}
        
        for block_name, items in data.items():
            if not isinstance(items, list):
                continue
                
            for i, item in enumerate(items):
                sources = [
                    item.get("gpt_text"),
                    item.get("excerpt"),
                    item.get("text")
                ]
                for text in sources:
                    if text and isinstance(text, str) and text.strip():
                        texts[f"{block_name}_{i}"] = text.strip()
                        break
                        
        return texts

    def _log_text_source(self, data: Dict[str, Any], selected_text: str) -> None:
        """Логирует источник текста для GPT"""
        print("\n🔍 Источник текста для GPT:")
        print(f"  - Длина: {len(selected_text)} символов")
        print(f"  - Пример: {selected_text[:200]}...")

    def _detect_text_source(self, data: Dict[str, Any], text: str) -> str:
        """Определяет источник текста для метаданных"""
        sources = {
            "gpt_text": data.get("gpt_text"),
            "excerpt": data.get("excerpt"),
            "text": data.get("text")
        }
        
        for name, source_text in sources.items():
            if source_text and source_text.strip() == text.strip():
                return name
                
        return "nested_text"

    def _get_model_info(self) -> str:
        """Возвращает информацию о используемой модели"""
        if gpt4all_model:
            return f"GPT4All-{os.path.basename(gpt4all_model_path)}"
        elif openai:
            return "OpenAI-gpt-3.5-turbo"
        return "unknown"

    def _save_debug(self, name: str, content: str) -> None:
        """Сохраняет отладочную информацию в файл"""
        try:
            log_dir = Path("logs/gpt_debug")
            log_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            with open(log_dir / f"{name}_{ts}.txt", "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            print(f"⚠️ Не удалось сохранить {name}-лог: {e}")