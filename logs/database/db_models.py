from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
import yaml
import os
from datetime import datetime

Base = declarative_base()


class Trade(Base):
    __tablename__ = 'trades'

    id = Column(Integer, primary_key=True)
    symbol = Column(String(10))
    entry_price = Column(Float)
    exit_price = Column(Float)
    quantity = Column(Float)
    entry_time = Column(DateTime, default=datetime.utcnow)
    exit_time = Column(DateTime)
    pnl = Column(Float)
    strategy = Column(String(50))
    status = Column(String(20), default='open')


def init_db():
    try:
        config_path = os.path.join(os.path.dirname(__file__), '../../config/config.yaml')
        with open(config_path) as file:
            config = yaml.safe_load(file)

        db_config = config['database']
        # Updated connection string with auth plugin
        connection_string = (
            f"mysql+pymysql://{db_config['user']}:{db_config['password']}@"
            f"{db_config['host']}/{db_config['database']}?"
            f"auth_plugin=mysql_native_password"
        )

        engine = create_engine(connection_string, echo=True)
        Base.metadata.create_all(engine)

        Session = sessionmaker(bind=engine)
        return Session()
    except Exception as e:
        print(f"Error initializing database: {e}")
        raise


if __name__ == "__main__":
    session = init_db()
    print("Database connection successful!")