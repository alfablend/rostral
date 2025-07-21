from flask import Blueprint, request, jsonify
from .service import run_pipeline

bp = Blueprint('api', __name__)

@bp.route('/monitor', methods=['POST'])
def start_monitoring():
    data = request.json
    result = run_pipeline(data['template'])
    return jsonify({"status": "success", "data": result})