from flask import Flask, jsonify
from rostral.runner import PipelineRunner  # Абсолютный импорт
from rostral.models import load_yaml_config

app = Flask(__name__)

@app.route('/monitor', methods=['POST'])
def monitor():
    config = load_yaml_config("templates/news.yaml")
    runner = PipelineRunner(config)
    result = runner.run()
    return jsonify(result)

if __name__ == '__main__':
    app.run()