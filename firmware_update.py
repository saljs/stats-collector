import requests
from data_interface import DataInterface
from io import BytesIO
from logging import Logger
from zipfile import ZipFile

def get_firmware_archive(db: DataInterface, uri: str, logger: Logger):
    """Downloads the latest firmware archive and adds entries to the database."""
    logger.info("Dowloading firmware.")
    with requests.get(uri) as response:
        if response.ok:
            with ZipFile(BytesIO(response.content)) as archive:
                db.add_firmware(archive)
            logger.info("Firmware info updated.")
        else:
            logger.warning(f"Firmware archive download failed ({response.status_code}).")
