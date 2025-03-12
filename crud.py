from sqlalchemy.orm import Session
import models

def read_parking_lot(parking_lot_id: int, db):
    result = db.query(models.ParkingLots).filter(models.ParkingLots.id == parking_lot_id).first()
    return result

def read_all_parking_lots(db):
    result = db.query(models.ParkingLots).all()
    return result

def create_parking_lot(name: str, latitude: float, longitude: float, location_name: str, free_spots: int, capacity: int, db):
    db_parking_lot = models.ParkingLots(name=name, latitude=latitude, longitude=longitude, location_name=location_name, free_spots=free_spots, capacity=capacity)
    db.add(db_parking_lot)
    db.commit()
    db.refresh(db_parking_lot)

def update_parking_lot(parking_lot_id: int, name: str, latitude: float, longitude: float, location_name: str, free_spots: int, capacity: int, db):
    result = db.query(models.ParkingLots).filter(models.ParkingLots.id == parking_lot_id).update({"name": name, "latitude": latitude, "longitude": longitude, "location_name": location_name, "free_spots": free_spots, "capacity": capacity})
    if not result:
        return None
    db.commit()
    return result

def delete_parking_lot(parking_lot_id: int, db):
    if not db.query(models.ParkingLots).where(models.ParkingLots.id == parking_lot_id).first():
        return None
    result = db.query(models.ParkingLots).where(models.ParkingLots.id == parking_lot_id).delete()
    db.commit()
    return result

def read_cameras(camera_id: int, db):
    result = db.query(models.Cameras).filter(models.Cameras.id == camera_id).first()
    return result

def read_all_cameras(db):
    result = db.query(models.Cameras).all()
    return result

def create_camera(name: str, parking_lot_id: int, api: str, config, db):
    db_camera = models.Cameras(name=name, parking_lot_id=parking_lot_id, api=api, config=config)
    db.add(db_camera)
    db.commit()
    db.refresh(db_camera)

def update_camera(camera_id: int, name: str, parking_lot_id: int, api: str, config, db):
    result = db.query(models.Cameras).filter(models.Cameras.id == camera_id).update({"name": name, "parking_lot_id": parking_lot_id, "api": api, "config": config})
    if not result:
        return None
    db.commit()
    return result

def delete_camera(camera_id: int, db):
    if not db.query(models.Cameras).where(models.Cameras.id == camera_id).first():
        return None
    result = db.query(models.Cameras).where(models.Cameras.id == camera_id).delete()
    db.commit()
    return result

def read_user(user_id: int, db):
    result = db.query(models.Users).filter(models.Users.id == user_id).first()
    return result

def read_all_users(db):
    result = db.query(models.Users).all()
    return result

def update_user(user_id: int, username: str, password: str, is_superior: bool, db):
    result = db.query(models.Users).filter(models.Users.id == user_id).update({"username": username, "hashed_password": password, "is_superior": is_superior})
    if not result:
        return None
    db.commit()
    return result

def delete_user(user_id: int, db):
    if not db.query(models.Users).where(models.Users.id == user_id).first():
        return None
    result = db.query(models.Users).where(models.Users.id == user_id).delete()
    db.commit()
    return result
