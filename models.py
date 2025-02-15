from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Float, JSON
from db_main import Base


class ParkingLots(Base):
    __tablename__ = 'parking_lots'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    latitude = Column(Float, index=True)
    longitude = Column(Float, index=True)
    location_name = Column(String, index=True)
    free_spots = Column(Integer, index=True)
    capacity = Column(Integer, index=True)

class Users(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True)
    hashed_password = Column(String)
    is_superior = Column(Boolean)

class Cameras(Base):
    __tablename__ = 'cameras'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    parking_lot_id = Column(Integer, ForeignKey(ParkingLots.id))
    api = Column(String, unique=True)
    config = Column(JSON)
