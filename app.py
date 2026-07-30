"""
app.py
------
Local Flask server. Chrome mein http://127.0.0.1:5000 khol ke use karo.

Left side: URL input box + Fetch button
Right side: scrape ho ke aaya hua data (A to Z)

Naya module (jaise pincode delivery check) add karna ho to:
  1. scraper.py mein naya function likho
  2. Neeche ek naya route (@app.route("/api/xyz")) bana ke usko call karo
  3. Frontend (static/script.js) se us route ko hit karo
"""

from flask import Flask, render_template, request, jsonify
from scraper import scrape_product_page

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/fetch", methods=["POST"])
def api_fetch():
    payload = request.get_json(silent=True) or {}
    url = (payload.get("url") or "").strip()

    if not url:
        return jsonify({"ok": False, "error": "URL do bhai, khaali box bheja hai."}), 400

    if not url.startswith("http"):
        return jsonify({"ok": False, "error": "Ye valid URL nahi lag raha (http/https se start hona chahiye)."}), 400

    try:
        data = scrape_product_page(url)
        return jsonify({"ok": True, "data": data})
    except Exception as exc:  # noqa: BLE001 - user ko readable error dikhana hai
        return jsonify({"ok": False, "error": f"Fetch fail ho gaya: {exc}"}), 500

@app.route("/api/check-pincodes", methods=["POST"])
def api_check_pincodes():
    payload = request.get_json(silent=True) or {}
    url = (payload.get("url") or "").strip()

    if not url:
        return jsonify({"ok": False, "error": "URL missing."}), 400

    try:
        import json
        import os
        # Load pincodes from local JSON
        if not os.path.exists("pincodes.json"):
            return jsonify({"ok": False, "error": "pincodes.json file nahi mili root folder mein."}), 400
            
        with open("pincodes.json", "r") as f:
            pincodes = json.load(f)
            
        if not pincodes or not isinstance(pincodes, list):
            return jsonify({"ok": False, "error": "pincodes.json mein valid array nahi hai."}), 400

        from scraper import check_pincodes_bulk
        analytics_data = check_pincodes_bulk(url, pincodes)
        return jsonify({"ok": True, "data": analytics_data})
        
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


# Naya code (Replace karo):
if __name__ == "__main__":
    app.run(debug=False, port=5000)
