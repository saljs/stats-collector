import datetime
import hashlib
import re
from typing import Any, Dict, List, Optional
from zipfile import ZipFile
from sqlalchemy import (
    create_engine,
    text,
    Column,
    DateTime,
    Integer,
    Float,
    LargeBinary,
    MetaData,
    String,
    Table,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
)

FW_FILE_RE = re.compile(r"^(\w+)-((\d+\.)*\d+)-([a-fA-F0-9]{32})\.bin")
DB_STR_LEN = 256

class Base(DeclarativeBase):
    """Base class for object models."""
    pass

class MonitorNode(Base):
    """Represents data about particular nodes submitting stats. By default,
    nodes do not have descriptive names, so they will need to be added by an
    API call."""
    __tablename__ = "nodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(DB_STR_LEN), nullable=True)
    last_ip: Mapped[str] = mapped_column(String(DB_STR_LEN), nullable=True)

    def as_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "last_ip": self.last_ip,
        }

class FirmwareFile(Base):
    """Represents a firmware file for one or more monitors."""
    __tablename__ = "firmware_files"

    name: Mapped[str] = mapped_column(String(DB_STR_LEN), primary_key=True)
    lib_version: Mapped[str] = mapped_column(String(DB_STR_LEN))
    hash: Mapped[str] = mapped_column(String(DB_STR_LEN))
    firmware: Mapped[bytes] = mapped_column(LargeBinary(4194304)) # 4MB per row

    @property
    def version(self) -> str:
        return f"{self.name}-{self.lib_version}-{self.hash}"

    @classmethod
    def from_file(cls, fname: str, fdata: bytes) -> "FirmwareFile":
        """Returns a `FirmwareFile` object from a filename/data combo. The
        file name should be just the basename, without leading directory info.
        """
        # Filenames are in the format [name]-[lib_version]-[hash].bin
        #    Such as: donna-1.1.1-63e15f1a281f0616358747a11026899a.bin
        finfo = FW_FILE_RE.match(fname)
        if finfo is None:
            raise AttributeError("file name is invalid.")

        return cls(
            name = finfo.group(1),
            lib_version = finfo.group(2),
            hash = finfo.group(4),
            firmware = fdata,
        )

    def as_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "lib_version": self.lib_version,
            "hash": self.hash,
            "version": self.version,
            "firmware": self.firmware,
        }

class StatsInstance(Base):
    """Represents a stats instance passed by a monitor."""
    __tablename__ = "stats_entries"

    entry_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id: Mapped[int] = mapped_column(Integer)
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True))
    high_temp: Mapped[float] = mapped_column(Float, nullable=True)
    low_temp: Mapped[float] = mapped_column(Float, nullable=True)
    air_temp: Mapped[float] = mapped_column(Float, nullable=True)
    humidity: Mapped[float] = mapped_column(Float, nullable=True)

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

    def __init__(self, conn_string: str):
        """Initialize a database engine and make sure all tables are created."""
        self._engine = create_engine(conn_string)
        Base.metadata.create_all(self._engine)

    def ingest(self, stats: Dict[str, Any], ip: Optional[str] = None):
        """Add a new stats instance to the database."""
        instance = StatsInstance.from_dict(stats)
        with Session(self._engine) as session:
            nodeInfo = session.query(MonitorNode).filter(MonitorNode.id == stats["id"]).one_or_none()
            if nodeInfo is None:
                # Add entry to node list
                nodeInfo = MonitorNode(id=stats["id"], name=str(stats["id"]))
                session.add(nodeInfo)
            if ip is not None:
                nodeInfo.last_ip = ip
            session.add(instance)
            session.commit()

    def add_firmware(self, archive: ZipFile):
        """Adds the firmware files from an archive to the database."""
        with Session(self._engine) as session:
            for fname in archive.namelist():
                with archive.open(fname, "r") as fdata:
                    fw_new = FirmwareFile.from_file(fname, fdata.read())
                    fw_db = session.query(FirmwareFile).filter(FirmwareFile.name == fw_new.name).one_or_none()
                    if fw_db is None:
                        session.add(fw_new)
                    elif fw_db.version != fw_new.version:
                        fw_db.lib_version = fw_new.lib_version
                        fw_db.hash = fw_new.hash
                        fw_db.firmware = fw_new.firmware
            session.commit()

    def get_firmware(self, fw_name: str) -> Optional[Dict[str, Any]]:
        """Gets the current firmware with the given name."""
        with Session(self._engine) as session:
            fw = session.query(FirmwareFile).filter(FirmwareFile.name == fw_name).one_or_none()
            if fw is None:
                return None
            return fw.as_dict()

    def get_firmware_names(self) -> List[str]:
        """Gets a list of all firmware names."""
        with Session(self._engine) as session:
            names = session.query(FirmwareFile.name)
            return [r.name for r in names]

    def set_node_name(self, nodeId: int, name: str) -> Dict[str, Any]:
        """Sets the name of the node to the given value. If node does not exist, creates it."""
        if len(name) >= DB_STR_LEN:
            raise ValueError(f"The name {name} is longer than {DB_STR_LEN} characters.")
        with Session(self._engine) as session:
            nodeInfo = session.query(MonitorNode).filter(MonitorNode.id == nodeId).one_or_none()
            if nodeInfo is None:
                nodeInfo = MonitorNode(id=nodeId, name=name)
                session.add(nodeInfo)
            else:
                nodeInfo.name = name
            session.commit()
            return nodeInfo.as_dict()

    def get_nodes(self) -> List[Dict[str, Any]]:
        """Gets all of the monitor nodes from the node table."""
        with Session(self._engine) as session:
            nodes = session.query(MonitorNode)
            return [n.as_dict() for n in nodes]

    def update_schema(self):
        """Performs manual steps to update db schema from older versions."""
        with self._engine.connect() as conn:
            try:
                conn.execute(text("SELECT COUNT(entry_id) FROM stats_entries;"))
            except Exception as ex:
                # Create new tempory table
                tmp_meta = MetaData()
                new_table = Table(
                    "stats_entries_new",
                    tmp_meta,
                    *[ 
                        Column(
                            c.name, 
                            c.type,
                            primary_key = c.primary_key,
                            nullable = c.nullable,
                            autoincrement = c.autoincrement,
                        ) for c in StatsInstance.__table__.columns
                    ]
                )
                tmp_meta.create_all(bind=conn)
                #new_table.create(conn)

                # Copy data over
                cols = ",".join([c.name for c in StatsInstance.__table__.columns if c.name != "entry_id"])
                conn.execute(text(
                    f"INSERT INTO stats_entries_new ({cols}) SELECT * FROM stats_entries;"
                ))

                # Drop old table
                StatsInstance.__table__.drop(conn)

                # Rename table
                conn.execute(text(
                    "ALTER TABLE stats_entries_new RENAME TO stats_entries;"
                ))

                # Commit
                conn.commit()
