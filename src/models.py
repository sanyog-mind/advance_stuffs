
from sqlalchemy import Boolean, Column, Integer, String, ForeignKey, TIMESTAMP, text, DateTime
from sqlalchemy import MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base(metadata=MetaData(schema="public"))


