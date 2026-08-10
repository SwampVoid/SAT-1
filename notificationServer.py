import base64
import requests
from flask import Flask, request, jsonify, url_for, send_from_directory
from flask_cors import CORS

def start():
    app = Flask(__name__)
    CORS(app)

    # Module-level store so it persists across requests
    notificationsData = {
        "notification1": {
            "type": "Motion",
            "location": "Kitchen",
            "img": "/Icons/kitchenPicturePicture.jpg"
        },
    }
    next_id = 2  # simple counter for generating new keys

    @app.route('/Icons/<path:filename>')
    def serve_icon(filename):
        return send_from_directory('Icons', filename)

    @app.route("/notifications", methods=["GET"])
    def get_notifications():
        return jsonify(notificationsData), 200

    @app.route("/notifications", methods=["POST"])
    
    def add_notification():
        nonlocal next_id

        body = request.get_json()

        if not body or "type" not in body or "location" not in body:
            return jsonify({"error": "Missing required fields"}), 400

        new_key = f"notification{next_id}"
        notificationsData[new_key] = {
            "type": body["type"],
            "location": body["location"],
            "img": body.get("img", "")  # optional, default empty
        }
        next_id += 1

        return jsonify({new_key: notificationsData[new_key]}), 201
    
    app.run(debug=True, use_reloader=False, port=5001)

    
        
        