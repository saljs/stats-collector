import os
from flask import Flask, request
from data_interface import DataInterface

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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
