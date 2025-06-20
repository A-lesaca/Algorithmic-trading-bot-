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
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)

        db_config = config['data']
        print(f"Loaded DB config: {db_config}")

        # Updated connection string with additional parameters
        connection_string = (
            f"mysql+pymysql://{db_config['user']}:{db_config['password']}@"
            f"{db_config['host']}/{db_config['data']}?"
            f"charset=utf8mb4&ssl_disabled=True"
        )

        engine = create_engine(connection_string, echo=True, pool_pre_ping=True)

        # Verify connection before creating tables
        with engine.connect() as test_conn:
            test_conn.execute("SELECT 1")

        Base.metadata.create_all(engine)
        return sessionmaker(bind=engine)()

    except yaml.YAMLError as e:
        print(f"❌ YAML config error: {e}")
        raise
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        raise
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        raise


if __name__ == "__main__":
    try:
        session = init_db()
        print("✅ Database connection successful!")
        session.close()
    except Exception as e:
        print(f"❌Failed to initialize data: {str(e)}")
        if "Access denied" in str(e):
            print("Check:")
            print("1. MySQL user credentials in config.yaml")
            print("2. User permissions in MySQL")
            print("3. MySQL server is running")