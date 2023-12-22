import os
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from flask import Flask, request
from data_interface import DataInterface
from firmware_update import get_firmware_archive

app = Flask(__name__)
db = DataInterface(
    os.environ.get("DB_CONN", "sqlite+pysqlite:///test.db"),
    debug="DEBUG" in os.environ,
)

@app.route('/', methods=['POST'])
def collect():
    stats = request.get_json()
    try:
        db.ingest(stats)
        return "Success", 200
    except AttributeError:
        return "Bad Request", 400

@app.route('/', methods=['GET'])
def homepage():
    return "Vivarium stats server version 1.2", 200
    
@app.route('/fw/<fwname>', methods=['GET', 'POST'])
def firmware(fwname: str):
    fw = db.get_firmware(fwname)
    if fw is None:
        return "Bad Request", 400
    if request.method == "GET":
        return json.jsonify(vars(fw))
    # TODO: update logic
    return "Bad Request", 400

if __name__ == "__main__":
    scheduler = BackgroundScheduler()
    if "FIRMWARE_URL" in os.environ:
        scheduler.add_job(
            get_firmware_archive,
            trigger = "interval",
            args = (db, os.environ.get("FIRMWARE_URL")),
            hours = 3,
            start_date = datetime.now()
        )
        scheduler.start()
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
