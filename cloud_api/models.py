from sqlalchemy import Column, Integer, String, DateTime
import datetime
from .db import Base

class DeviceRecord(Base):
    __tablename__ = 'device_records'
    id = Column(Integer, primary_key=True, index=True)
    email_enc = Column(String, nullable=True)
    phone_enc = Column(String, nullable=True)
    serial_enc = Column(String, nullable=True)
    device_type = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    email_enc = Column(String, nullable=False)
    serial_enc = Column(String, nullable=True)
    role = Column(String, nullable=False, default='user')
    created_at = Column(DateTime, default=datetime.datetime.utcnow)