from rostral.runner import PipelineRunner
from rostral.models import load_yaml_config

def run_pipeline(template_name: str):
    """Адаптер для PipelineRunner"""
    config = load_yaml_config(f"templates/{template_name}.yaml")
    return PipelineRunner(config).run()

