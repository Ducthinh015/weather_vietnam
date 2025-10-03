from flask import Blueprint, jsonify
import logging

irrigation_bp = Blueprint("irrigation", __name__)
logger = logging.getLogger(__name__)


@irrigation_bp.route("/irrigation/advice", methods=["GET"])
def irrigation_advice():
    # Placeholder logic; can be expanded based on forecast thresholds
    return jsonify({
        "advice": "If humidity > 75% in upcoming hours, postpone irrigation; otherwise irrigate as per soil needs.",
        "thresholds": {"humidity": 75}
    })
