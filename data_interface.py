import datetime
from random import randrange
from typing import Any, Dict

from sqlalchemy import create_engine, DateTime, Integer, Float, String
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
)

class Base(DeclarativeBase):
    """Base class for object models."""
    pass

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
    def from_dict(cls, stats: Dict[str, Any]):
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
            # Add in a random milliseconds component, to prevent updates soming in at the same time
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

    def __init__(self, conn_string:str, debug:bool = False):
        """Initialize a database engine and make sure all tables are created."""
        self._engine = create_engine(conn_string, echo=debug)
        Base.metadata.create_all(self._engine)

    def ingest(self, stats: Dict[str, Any]):
        """Add a new stats instance to the database."""
        instance = StatsInstance.from_dict(stats)
        with Session(self._engine) as session:
            session.add(instance)
            session.commit()
