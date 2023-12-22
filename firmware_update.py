import io
import requests
from data_interface import DataInterface
from zipfile import ZipFile

def get_firmware_archive(db: DataInterface, uri: str):
    """Downloads the latest firmware archive and adds entries to the database."""
    with requests.get(uri) as response:
        if response.ok:
            with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
                db.add_firmware(archive)
