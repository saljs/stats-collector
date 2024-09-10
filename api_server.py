import os
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, json, request, send_file
from io import BytesIO
from data_interface import DataInterface
from firmware_update import get_firmware_archive

if "DEBUG" in os.environ:
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.DEBUG)

app = Flask(__name__)
db = DataInterface(os.environ.get("DB_CONN", "sqlite+pysqlite:///test.db"))
db.update_schema()

scheduler = BackgroundScheduler()
if "FIRMWARE_URL" in os.environ:
    get_firmware_archive(db, os.environ["FIRMWARE_URL"], app.logger)
    scheduler.add_job(
        get_firmware_archive,
        trigger = "interval",
        args = (db, os.environ["FIRMWARE_URL"], app.logger),
        hours = 3,
        max_instances = 1,
    )
    scheduler.start()

@app.route('/', methods=['POST'])
def collect():
    stats = request.get_json()
    try:
        db.ingest(stats, request.remote_addr)
        return "Success", 200
    except AttributeError:
        return "Bad Request", 400

@app.route('/', methods=['GET'])
def homepage():
    return "Vivarium stats server version 1.3", 200

@app.route('/fw', methods=['GET'])
def firmware_list():
    fwlist = db.get_firmware_names()
    return json.jsonify(fwlist)

@app.route('/fw/<fwname>', methods=['GET'])
def firmware(fwname: str):
    fw = db.get_firmware(fwname)
    if fw is None:
        return "Not Found", 404
    if "X-FWVER" in request.headers:
        if request.headers["X-FWVER"] == fw["version"]:
            # No new update available
            return "Not Modified", 304
        app.logger.info(f"Sending updated firmware file: {fw['version']}")
        return send_file(
            BytesIO(fw["firmware"]),
            mimetype = "application/octet-stream",
            as_attachment = True,
            download_name = f"{fw['version']}.bin",
        )
    # Ignore firmware bytes, send metadata
    fw.pop("firmware")
    return json.jsonify(fw)

@app.route('/nodes', methods=['GET'])
def node_list():
    return json.jsonify(db.get_nodes())

@app.route('/nodes/<int:nodeId>', methods=['POST'])
def name_node(nodeId: int):
    if "name" not in request.values:
        return "Bad Request", 400
    return json.jsonify(db.set_node_name(nodeId, request.values["name"]))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug = True, host = "0.0.0.0", port = port)
