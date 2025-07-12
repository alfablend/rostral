import os
import re
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
from io import BytesIO
from datetime import datetime
from typing import Dict, Any, List
import typer
from .base import PipelineStage

# Чтение лимитов из переменных окружения
MAX_FRAGMENT_LENGTH = int(os.getenv("GPT_FRAGMENT_MAX_LENGTH", 200))
TEXT_MAX_LENGTH = int(os.getenv("GPT_TEXT_MAX_LENGTH", 2000))
CHUNK_HEAD = int(os.getenv("GPT_CHUNK_HEAD", TEXT_MAX_LENGTH // 2))
CHUNK_TAIL = int(os.getenv("GPT_CHUNK_TAIL", TEXT_MAX_LENGTH // 2))

# Утилита извлечения ключевых фрагментов из текста
def extract_text_fragments(text: str, keywords: List[str], max_fragment_length=MAX_FRAGMENT_LENGTH, total_max_length=TEXT_MAX_LENGTH) -> str:
    fragments = []
    pattern = r'(?:' + '|'.join(
        r'\b' + re.escape(k.lower()) + r'\w*\b' for k in keywords
    ) + r')'

    for match in re.finditer(pattern, text, flags=re.IGNORECASE):
        start = match.start()
        end = text.find('.', start)
        end = end + 1 if end != -1 else len(text)
        fragment = text[start:end].strip()
        if len(fragment) > max_fragment_length:
            fragment = fragment[:max_fragment_length] + '...'
        fragments.append(fragment)

    excerpt = ' '.join(fragments)
    return excerpt[:CHUNK_HEAD] + ' ... ' + excerpt[-CHUNK_TAIL:] if len(excerpt) > total_max_length else excerpt

# Основной класс
class ProcessingStage(PipelineStage):
    """
    Универсальный обработчик PDF-файлов:
    - Извлекает текст из PDF
    - Генерирует excerpt по ключевым словам
    - Готовит gpt_text
    """

    def run(self, data: Dict[str, Any]) -> Dict[str, Any]:
        
        processing_meta = {
            "timestamp": datetime.now().isoformat(),
            "processed_files": 0,
            "errors": []
        }

        typer.echo(f"⚙️ ProcessingStage input data: {type(data)}")
        typer.echo(f"📐 ENV limits: fragment={MAX_FRAGMENT_LENGTH}, gpt_text={TEXT_MAX_LENGTH}, head={CHUNK_HEAD}, tail={CHUNK_TAIL}")

        if not isinstance(data, dict):
            typer.echo("ℹ️ Input data is not a dictionary, skipping processing")
            return data

        for block_name, items in data.items():
            if not isinstance(items, list):
                typer.echo(f"🔸 Skipping block '{block_name}' (not a list)")
                continue

            typer.echo(f"🔧 Processing block '{block_name}' with {len(items)} items")

            for record in items:
                if not isinstance(record, dict):
                    continue

                self._process_record(record, processing_meta)

        data["__processing__"] = processing_meta
        typer.echo(f"✅ Processed {processing_meta['processed_files']} PDF files")

        if "events" in data:
            for i, event in enumerate(data.get("events", [])):
                typer.echo(f"📄 Документ #{i+1}: {event.get('title', 'Без названия')}")
        else:
            typer.echo("❌ 'events' отсутствует")

        return data

    def _process_record(self, record: Dict[str, Any], meta: Dict[str, Any]) -> None:
        if not record.get("file_content") or ".pdf" not in record.get("url", "").lower():
            typer.echo("❌ Файл не PDF, пропуск")
            return

        try:
            text = self._extract_pdf_text(record["file_content"])
            record["text"] = text
            del record["file_content"]
            meta["processed_files"] += 1
            typer.echo(f"📝 Extracted text from PDF ({len(text)} chars)")
        except Exception as e:
            error_msg = f"Failed to process PDF: {str(e)}"
            record["text"] = f"[ERROR: {error_msg}]"
            record["error"] = error_msg
            meta["errors"].append({
                "url": record.get("url", "unknown"),
                "error": error_msg
            })
            typer.echo(f"❌ {error_msg}")
            return

        # Ключевые слова из конфигурации
        keywords = getattr(self.config.processing, "extract_keywords", [])
        if keywords:
            excerpt = extract_text_fragments(text, keywords)
            record["excerpt"] = excerpt
            typer.echo(f"🔍 excerpt by keywords → {len(excerpt)} chars")
            
            # Use excerpt as gpt_text if available
            record["gpt_text"] = excerpt
            typer.echo(f"✂️ gpt_text set to excerpt ({len(excerpt)} chars)")
        else:
            # Fallback to original behavior if no keywords/excerpt
            if len(text) > TEXT_MAX_LENGTH:
                record["gpt_text"] = f"{text[:CHUNK_HEAD]} ... {text[-CHUNK_TAIL:]}"
                typer.echo(f"✂️ gpt_text trimmed from full text to {len(record['gpt_text'])} chars")
            else:
                record["gpt_text"] = text

    def _extract_pdf_text(self, pdf_content: bytes, max_pages: int = 10) -> str:
        text_parts = []
        doc = fitz.open(stream=BytesIO(pdf_content), filetype="pdf")

        for page_num in range(min(len(doc), max_pages)):
            page = doc.load_page(page_num)
            text = self._extract_page_text(page)
            if text:
                text_parts.append(text)

        return "\n".join(text_parts).strip()

    def _extract_page_text(self, page) -> str:
        text = page.get_text().strip()
        if text:
            return text

        try:
            pix = page.get_pixmap(dpi=300)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            return pytesseract.image_to_string(img, lang="rus+eng").strip()
        except Exception as e:
            return f"[OCR failed: {str(e)}]"
