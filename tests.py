import unittest
import io
import zipfile
from contextlib import contextmanager
from pathlib import Path

import data_interface as DI
from api_server import app, db

@contextmanager
def mock_firmware_archive():
    zip_buffer = io.BytesIO()
    try:
        zip_file = zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False)
        for file_name, data in [
            ("fw1-1.2.3-8ddd8be4b179a529afa5f2ffae4b9858.bin", io.BytesIO(b'111')),
            ("fw2-1-3858f62230ac3c915f300c664312c63f.bin", io.BytesIO(b'222')),
            ("fw3-2.4-85dbd03215461e59b6c6a163b80229a1.bin", io.BytesIO(b'333')),
        ]:
            zip_file.writestr(file_name, data.getvalue())
        yield zip_file
    finally:
        zip_file.close()

def mock_stats():
    return {
        "id": 12345,
        "timestamp": "2020-03-20T14:30:43",
        "high_temp": 24.5,
        "low_temp": 20.0,
        "air_temp": 22.24,
        "humidity": 72,
        "digital_1": 0,
        "digital_2": 1,
        "analog": 135,
    }

class TestDataInterface(unittest.TestCase):
    def setUp(self):
        # Create an in-memory database
        self.db = DI.DataInterface("sqlite://")

        # Add some stats to the databse
        stats = mock_stats()
        self.db.ingest(stats)
        stats["id"] = 23456
        self.db.ingest(stats, "10.3.0.1")
    
    def test_add_firmware(self):
        with mock_firmware_archive() as zipfile:
            self.db.add_firmware(zipfile)
        # Confirm firmware is in the database
        self.assertEqual(len(self.db.get_firmware_names()), 3)
        fw1 = self.db.get_firmware("fw1")
        self.assertIsNotNone(fw1)
        self.assertEqual(fw1["lib_version"], "1.2.3")
        self.assertEqual(fw1["hash"], "8ddd8be4b179a529afa5f2ffae4b9858")
        self.assertEqual(fw1["firmware"], b'111')
        fw2 = self.db.get_firmware("fw2")
        self.assertIsNotNone(fw2)
        self.assertEqual(fw2["lib_version"], "1")
        self.assertEqual(fw2["hash"], "3858f62230ac3c915f300c664312c63f")
        self.assertEqual(fw2["firmware"], b'222')
        fw3 = self.db.get_firmware("fw3")
        self.assertIsNotNone(fw3)
        self.assertEqual(fw3["lib_version"], "2.4")
        self.assertEqual(fw3["hash"], "85dbd03215461e59b6c6a163b80229a1")
        self.assertEqual(fw3["firmware"], b'333')

    def test_add_firmware_fails_bad_file(self):
        # Mock a firmware archive
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            for file_name, data in [
                ("fw1-1.2.3-8ddd8be4b179a529afa5f2ffae4b9858.bin", io.BytesIO(b'111')),
                ("fw2-1-3858f62230ac3c915f300c664312c63f.bin", io.BytesIO(b'222')),
                ("hello_world.txt", io.BytesIO(b'Hello world!')),
            ]:
                zip_file.writestr(file_name, data.getvalue())
            with self.assertRaises(AttributeError):
                self.db.add_firmware(zip_file)
        # Confirm no firmware files written to DB
        self.assertEqual(len(self.db.get_firmware_names()), 0)

    def test_nodes(self):
        # Check that we have 2 nodes
        nodes = self.db.get_nodes()
        self.assertEqual(len(nodes), 2)
        # Check name of the the first node
        node1 = next(n for n in nodes if n["id"] == 12345)
        self.assertEqual(node1["name"], "12345")
        self.assertIsNone(node1["last_ip"])
        # Change the name of the first node
        self.db.set_node_name(12345, "Test Node 1")
        # Read nodes back in
        nodes = self.db.get_nodes()
        self.assertEqual(len(nodes), 2)
        node1 = next(n for n in nodes if n["id"] == 12345)
        self.assertEqual(node1["name"], "Test Node 1")
        # Make sure node2 has ip set
        node2 = next(n for n in nodes if n["id"] == 23456)
        self.assertEqual(node2["name"], "23456")
        self.assertEqual(node2["last_ip"], "10.3.0.1")
        # Set the name of a non-existant node
        self.db.set_node_name(44444, "Test Node 3")
        # Read nodes back in
        nodes = self.db.get_nodes()
        self.assertEqual(len(nodes), 3)
        node3 = next(n for n in nodes if n["id"] == 44444)
        self.assertEqual(node3["name"], "Test Node 3")
        self.assertIsNone(node3["last_ip"])

    def test_node_fails_name_too_long(self):
        with self.assertRaises(ValueError):
            self.db.set_node_name(99999, "12ab" * 100)
        self.assertEqual(len(self.db.get_nodes()), 2)


class TestEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config.update({
            "TESTING": True,
        })
        with mock_firmware_archive() as zipfile:
            db.add_firmware(zipfile)

    def test_homepage(self):
        client = app.test_client()
        response = client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_firmware(self):
        client = app.test_client()
        response = client.get("/fw")
        self.assertEqual(response.status_code, 200)
        self.assertIn("fw1", response.json)
        self.assertIn("fw2", response.json)
        self.assertIn("fw3", response.json)
        
        response = client.get("/fw/fw1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["lib_version"], "1.2.3")
        self.assertEqual(response.json["hash"], "8ddd8be4b179a529afa5f2ffae4b9858")
        
        response = client.get("/fw/none")
        self.assertEqual(response.status_code, 404)
        
        response = client.get("/fw/fw1", headers={"X-FWVER": "fw1-1.2.2-8ddd8be4b179a529afa5f2ffae4b9858"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, b'111')
        
        response = client.get("/fw/fw1", headers={"X-FWVER": "fw1-1.2.3-8ddd8be4b179a529afa5f2ffae4b9858"})
        self.assertEqual(response.status_code, 304)
    
    def test_request_flow(self):
        self.step_post_stats()
        self.step_check_node()
        self.step_rename_node()

    def step_post_stats(self):
        client = app.test_client()
        response = client.post("/", json=mock_stats())
        self.assertEqual(response.status_code, 200)

        null_stats = mock_stats()
        null_stats["humidity"] = None
        response = client.post("/", json=null_stats)
        self.assertEqual(response.status_code, 200)

        bad_stats = mock_stats()
        del bad_stats["digital_1"]
        response = client.post("/", json=bad_stats)
        self.assertEqual(response.status_code, 400)
    
    def step_check_node(self):
        client = app.test_client()
        response = client.get("/nodes")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json[0]["id"], 12345)
        self.assertEqual(response.json[0]["name"], "12345")
        self.assertEqual(response.json[0]["last_ip"], "127.0.0.1")

    def step_rename_node(self):
        client = app.test_client()
        response = client.post("/nodes/12345", data={"name": "Test Node 1"})
        self.assertEqual(response.status_code, 200)
        response = client.post("/nodes/12345", data={"foo": "Test Node 1"})
        self.assertEqual(response.status_code, 400)
        response = client.post("/nodes/23456", data={"name": "Test Node 2"})
        self.assertEqual(response.status_code, 200)
        
        response = client.get("/nodes")
        self.assertEqual(response.json[0]["id"], 12345)
        self.assertEqual(response.json[0]["name"], "Test Node 1")
        self.assertEqual(response.json[1]["id"], 23456)
        self.assertEqual(response.json[1]["name"], "Test Node 2")
        self.assertEqual(response.json[1]["last_ip"], None)
