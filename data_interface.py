import datetime
import re
from random import randrange
from typing import Any, Dict, Optional

from sqlalchemy import (
    create_engine,
    DateTime,
    Integer,
    Float,
    LargeBytes,
    String,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
)

FW_FILE_RE = re.compile(r"^(\w+)-((\d+\.?)+\d+)-([a-fA-F0-9]{32})\.bin")

class Base(DeclarativeBase):
    """Base class for object models."""
    pass

class FirmwareFile(Base):
    """Represents a firmware file for one or more monitors."""
    __tablename__ = "firmware_files"

    name: Mapped[str] = mapped_column(String, primary_key=True)
    lib_version: Mapped[str] = mapped_column(String)
    checksum: Mapped[str] = mapped_column(String)
    hash: Mapped[str] = mapped_column(String)
    firmware: Mapped[bytes] = mapped_column(LargeBytes)

    @classmethod
    def from_file(cls, fname: str, fdata: bytes) -> "FirmwareFile":
        """Returns a `FirmwareFile` object from a filename/data combo. The
        file name should be just the basename, without leading directory info.
        """
        fhash = hashlib.md5(fdata).hexdigest()

        # Filenames are in the format [name]-[lib_version]-[checksum].bin
        #    Such as: donna-1.1.1-63e15f1a281f0616358747a11026899a.bin
        finfo = FW_FILE_RE.match(fname):
        if finfo is None:
            raise AttributeError("file name is invalid.")

        return cls(
            name = finfo.group(1)[0],
            lib_version = finfo.group(2)[0],
            checksum = finfo.group(3)[0],
            hash = fhash.lower(),
            firmware = fdata,
        )

class StatsInstance(Base):
    """Represents a stats instance passed by a monitor."""
    __tablename__ = "stats_entries"

    id: Mapped[int] = mapped_column(Integer)
    timestamp: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True
    )
    high_temp: Mapped[float] = mapped_column(Float)
    low_temp: Mapped[float] = mapped_column(Float)
    air_temp: Mapped[float] = mapped_column(Float)
    humidity: Mapped[float] = mapped_column(Float)

    digital_1: Mapped[int] = mapped_column(Integer)
    digital_2: Mapped[int] = mapped_column(Integer)
    analog: Mapped[int] = mapped_column(Integer)

    @classmethod
    def from_dict(cls, stats: Dict[str, Any]) -> "StatsInstance":
        if "id" not in stats:
            raise AttributeError("'id' not in dict.")
        elif "timestamp" not in stats:
            raise AttributeError("'timestamp' not in dict.")
        elif "high_temp" not in stats:
            raise AttributeError("'high_temp' not in dict.")
        elif "low_temp" not in stats:
            raise AttributeError("'low_temp' not in dict.")
        elif "air_temp" not in stats:
            raise AttributeError("'air_temp' not in dict.")
        elif "humidity" not in stats:
            raise AttributeError("'humidity' not in dict.")
        elif "digital_1" not in stats:
            raise AttributeError("'digital_1' not in dict.")
        elif "digital_2" not in stats:
            raise AttributeError("'digital_2' not in dict.")
        elif "analog" not in stats:
            raise AttributeError("'analog' not in dict.")

        timestamp = stats["timestamp"]
        if not isinstance(timestamp, datetime.datetime):
            timestamp = datetime.datetime.fromisoformat(timestamp).astimezone(datetime.timezone.utc)
            # Add in a random milliseconds component, to prevent updates coming in at the same time
            #   from different devices from conflicting.
            timestamp += datetime.timedelta(microseconds=randrange(1000000))

        return cls(
            id=stats["id"],
            timestamp=timestamp,
            high_temp=stats["high_temp"],
            low_temp=stats["low_temp"],
            air_temp=stats["air_temp"],
            humidity=stats["humidity"],
            digital_1=stats["digital_1"],
            digital_2=stats["digital_2"],
            analog=stats["analog"],
        )
     

class DataInterface:
    """Provides interface functions to the database."""

    def __init__(self, conn_string: str, debug: bool = False):
        """Initialize a database engine and make sure all tables are created."""
        self._engine = create_engine(conn_string, echo=debug)
        Base.metadata.create_all(self._engine)

    def ingest(self, stats: Dict[str, Any]):
        """Add a new stats instance to the database."""
        instance = StatsInstance.from_dict(stats)
        with Session(self._engine) as session:
            session.add(instance)
            session.commit()

    def add_firmware(self, archive: ZipFile):
        """Adds the firmware files from an archive to the database."""
        with Session(self._engine) as session:
            for fname in archive.namelist():
                with archive.open(fname, "r") as fdata:
                    fw_new = FirmwareFile.from_file(fname, fdata.read())
                    fw_db = sesion.query(FirmwareFile)
                        .filter_by(FirmwareFile.name == fw_new.name)
                        .one_or_none()
                    if fw_db is None:
                        session.add(fw_new)
                    elif fw_db.hash != fw_new.hash:
                        fw_db.lib_version = fw_new.lib_version
                        fw_db.checksum = fw_new.checksum
                        fw_db.hash = fw_new.hash
                        fw_db.firmware = fw_new.firmware
            session.commit()

    def get_firmware(self, fw_name: str) -> Optional[FirmwareFile]:
        """Gets the current firmware with the given name."""
        with Session(self._engine) as session:
            return session.query(FirmwareFile).filter_by(FirmwareFile.name == fw_name).one_or_none()
