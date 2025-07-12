# rostral/stages/base.py

from abc import ABC, abstractmethod
from jinja2 import Environment, BaseLoader
from datetime import datetime

class PipelineStage(ABC):
    """
    Abstract base class for all pipeline stages.
    Each stage receives input data and returns output to the next stage.
    Contains helper methods for Jinja2 rendering.
    """

    def __init__(self, config):
        self.config = config
        # Настраиваем окружение Jinja2 с функцией now()
        self.env = Environment(loader=BaseLoader())
        self.env.globals["now"] = datetime.now

    @abstractmethod
    def run(self, data):
        """
        Execute the stage logic.
        :param data: output from the previous stage (or None for the first stage)
        :return: result to be passed to the next stage
        """
        ...

    def render_url(self, template_str: str) -> str:
        """
        Рендерит Jinja2-шаблон строки (обычно URL),
        подставляя в него now() и другие глобальные функции.
        """
        tmpl = self.env.from_string(template_str)
        return tmpl.render()

    def render_payload(self, payload_template: dict) -> dict:
        """
        Рендерит Jinja2-шаблоны внутри словаря для POST-payload.
        """
        rendered = {}
        for k, v in payload_template.items():
            if isinstance(v, str):
                rendered[k] = self.env.from_string(v).render()
            else:
                rendered[k] = v
        return rendered
