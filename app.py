from pathlib import Path
from flask import Flask, jsonify, render_template, request, redirect
from rostral.runner import PipelineRunner 
from rostral.models import load_yaml_config
from rostral.db import Session, Event

app = Flask(__name__, template_folder="frontend/web_templates")


@app.route('/monitor', methods=['POST'])
def monitor():
    config = load_yaml_config("templates/news.yaml")
    runner = PipelineRunner(config)
    result = runner.run()
    return jsonify(result)

from flask import render_template

@app.route('/feed', methods=['GET'])
def feed():
    session = Session()
    events = session.query(Event).order_by(Event.timestamp.desc()).limit(50).all()
    session.close()
    return render_template("feed.html", events=events)



@app.route('/run', methods=['GET', 'POST'])
def run_template():
    templates = sorted(Path("templates").rglob("*.yaml")) + sorted(Path("templates").rglob("*.yml"))

    if request.method == 'POST':
        selected = request.form.get("template")  # ← это будет относительный путь
        config = load_yaml_config(str(Path("templates") / selected))
        PipelineRunner(config).run()
        return redirect("/feed")

    # передаём список относительных путей, как строки
    return render_template("run.html", templates=[str(t.relative_to("templates")) for t in templates])

if __name__ == '__main__':
    app.run()