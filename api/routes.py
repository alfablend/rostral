# api/routes.py
from flask import Blueprint, request, jsonify
from rostral.runner import PipelineRunner 
from rostral.models import load_yaml_config
import os

bp = Blueprint('api', __name__)

@bp.route('/monitor', methods=['POST'])
def monitor():
    try:
        # Путь к шаблону относительно корня проекта
        template_path = os.path.join("templates", request.json['template'])
        config = load_yaml_config(template_path)
        runner = PipelineRunner(config)
        result = runner.run()
        return jsonify({"status": "success", "data": result})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500