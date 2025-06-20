from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import yaml
import os

Base = declarative_base()


class Trade(Base):
    __tablename__ = 'trades'

    id = Column(Integer, primary_key=True)
    symbol = Column(String(10))
    entry_price = Column(Float)
    exit_price = Column(Float)
    quantity = Column(Float)
    entry_time = Column(DateTime)
    exit_time = Column(DateTime)
    pnl = Column(Float)
    strategy = Column(String(50))
    status = Column(String(20))


def init_db():
    config_path = os.path.join(os.path.dirname(__file__), '../../config/config.yaml')
    with open(config_path) as file:
        config = yaml.safe_load(file)

    db_config = config['database']
    connection_string = f"mysql+pymysql://{db_config['user']}:{db_config['password']}@{db_config['host']}/{db_config['database']}"

    engine = create_engine(connection_string)
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    return Session()