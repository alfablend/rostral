import sys, os

# add project root to sys.path to resolve 'stages' and 'models'
project_root = os.path.dirname(__file__)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import typer
from pathlib import Path
from typing import Optional
from rostral.runner import PipelineRunner
from rostral.models import load_yaml_config


import sys
import logging

# Настройка логгера
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("rostral.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ]
)

# Перенаправляем стандартный вывод в лог
class Tee:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, data):
        for s in self.streams:
            s.write(data)
            s.flush()

    def flush(self):
        for s in self.streams:
            s.flush()

sys.stdout = Tee(sys.stdout, open("rostral.log", "w", encoding="utf-8"))
sys.stderr = Tee(sys.stderr, open("rostral.log", "w", encoding="utf-8"))



app = typer.Typer(help="Rostral CLI — run monitoring pipelines from YAML templates.")

def list_templates(folder: Path) -> list[Path]:
    return sorted(folder.rglob("*.yaml")) + sorted(folder.rglob("*.yml"))

@app.command()
def monitor(
    config: Optional[Path] = typer.Argument(None, help="Path to YAML template"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Run without side effects"),
    once: bool = typer.Option(False, "--once", help="Run once and exit"),
    cron: Optional[str] = typer.Option(None, "--cron", help="Cron expression (e.g. '0 * * * *')")
):
    """
    Run a monitoring pipeline from a YAML template.
    """
    if config is None:
        templates = list_templates(Path("templates"))
        if not templates:
            typer.echo("❌ No templates found in templates/ folder.")
            raise typer.Exit()

        typer.echo("📂 Available templates:")
        for i, t in enumerate(templates):
            typer.echo(f"  [{i+1}] {t.as_posix()}")

        choice = typer.prompt("Select a template by number", type=int)
        if 1 <= choice <= len(templates):
            config = templates[choice - 1]
        else:
            typer.echo("❌ Invalid selection.")
            raise typer.Exit()

    cfg = load_yaml_config(str(config))
    runner = PipelineRunner(cfg)

    if cron:
        from croniter import croniter
        from datetime import datetime
        import time

        typer.echo(f"⏱ Running on schedule: {cron}")
        base = datetime.now()
        schedule = croniter(cron, base)
        while True:
            next_run = schedule.get_next(datetime)
            delay = (next_run - datetime.now()).total_seconds()
            typer.echo(f"⏳ Next run at {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
            time.sleep(max(0, delay))
            runner.run(dry_run=dry_run)
    else:
        # по умолчанию — выполняем один раз (dry_run учитывается)
        runner.run(dry_run=dry_run)

if __name__ == "__main__":
    app()
