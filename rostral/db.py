from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base

engine = create_engine("sqlite:///rostral_cache.db")
Session = sessionmaker(bind=engine)
Base.metadata.create_all(engine)