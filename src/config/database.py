import enum

from sqlalchemy import MetaData, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from src.config.db_config import loaded_config

Base = declarative_base(metadata=MetaData(schema="public"))


engine = create_engine(loaded_config.db_url, echo=False)

Session = sessionmaker(bind=engine)



# TODO : function to return session instance when invoked --> Close
def get_session():
    return Session()


def get_engine():
    return engine
