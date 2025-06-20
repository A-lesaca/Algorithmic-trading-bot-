import os
import yaml
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

Base = declarative_base()

class Trade(Base):
    __tablename__ = 'trades'

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False)
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=True)
    pnl = Column(Float, nullable=True)
    strategy = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

def init_db(config_path):
    """Initializes DB connection and returns a session."""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    db_url = config['database']['url']

    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()

__all__ = ['Trade', 'init_db']
