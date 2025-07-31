import sys
import logging
from pathlib import Path
from flask import Flask, jsonify, render_template, request, redirect
from rostral.runner import PipelineRunner 
from rostral.models import load_yaml_config
from rostral.db import Session, Event


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


app = Flask(__name__, template_folder="frontend/web_templates", static_folder='frontend/static')


@app.route('/monitor', methods=['POST'])
def monitor():
    config = load_yaml_config("templates/news.yaml")
    runner = PipelineRunner(config)
    result = runner.run()
    return jsonify(result)


@app.route('/')
def feed():
    session = Session()
    events = session.query(Event).order_by(Event.timestamp.desc()).all()
    session.close()

    # Загружаем список шаблонов
    templates = sorted(Path("templates").rglob("*.yaml")) + sorted(Path("templates").rglob("*.yml"))
    template_list = [str(t.relative_to("templates")) for t in templates]

    return render_template("feed.html", events=events, templates=template_list)

@app.route('/run', methods=['POST'])
def run_template():
    selected = request.form.get("template")
    config_path = str(Path("templates") / selected)

    try:
        config = load_yaml_config(config_path)
        PipelineRunner(config).run()
    except Exception as e:
        print(f"❌ Start-up error: {e}")

    return redirect("/")


if __name__ == '__main__':
    app.run()