# rostral/runner.py

import typer
from typer import colors

from rostral.stages.fetch import FetchStage
from rostral.stages.event_html import EventHTMLStage
from rostral.stages.extract import ExtractStage
from rostral.stages.json_extract import JsonExtractStage
from rostral.stages.event_json import EventJsonStage 
from rostral.stages.download import DownloadStage
from rostral.stages.normalize import NormalizeStage
from rostral.stages.processing import ProcessingStage
from rostral.stages.gpt import GPTStage
from rostral.stages.alert import AlertStage


class PipelineRunner:
    """
    PipelineRunner executes all configured stages in sequence.
    Each stage receives the output of the previous one.
    """

    def __init__(self, config):
        self.config = config
        self.stages = []

        # Always include fetch
        self.stages.append(FetchStage(config))

        # Conditionally include other stages
        if config.extract:
            # Выбираем стадию извлечения в зависимости от типа источника
            if config.source.type == "json":
                self.stages.append(JsonExtractStage(config))
                typer.echo("🧠 JsonExtractStage added: JSON processing activated")
                if getattr(config.download, "allow_json", False):
                    self.stages.append(EventJsonStage(config)) 
                    typer.echo("🧠 EventJsonStage added: JSON processing activated")          
            else:
                self.stages.append(ExtractStage(config))
        if config.download:
            self.stages.append(DownloadStage(config))
            typer.echo(f"Download config: {config.download}")

        if getattr(config.download, "allow_html", False):
            self.stages.append(EventHTMLStage(config))
            typer.echo("🧠 EventHTMLStage added: HTML processing activated")
            
        
        if config.processing:
            self.stages.append(ProcessingStage(config))
        if config.normalize:
            self.stages.append(NormalizeStage(config))
        if config.gpt:
            self.stages.append(GPTStage(config))
        if config.alert:
            self.stages.append(AlertStage(config))

    def run(self, dry_run: bool = False):
        typer.echo("🔧 self.config:")
        typer.echo(self.config.model_dump_json(indent=2))  # Для Pydantic v2
        # debug stages order
        typer.echo("\n🏷 Pipeline stages order:")
        for idx, stage in enumerate(self.stages, 1):
            typer.echo(f" {idx}. {stage.__class__.__name__}")
        typer.echo("")  

        
        context = {}
        data = None

        for stage in self.stages:
            stage_name = stage.__class__.__name__
            typer.secho(f"\n⏳ Starting stage: {stage_name}", fg=colors.YELLOW)

            data = stage.run(data or context)

            typer.secho(f"✅ Stage {stage_name} finished", fg=colors.GREEN)

            if isinstance(data, dict):
                context.update(data)
            else:
                context[stage_name] = data

        if dry_run:
            typer.echo("\n📝 Dry-run finished. Context:")
            for k, v in context.items():
                snippet = str(v)[:200] + ("..." if len(str(v)) > 200 else "")
                typer.echo(f"  {k}: {snippet}")

        return context
