from fastapi import FastAPI, Depends, HTTPException, status, File, UploadFile
from fastapi.security import HTTPBearer
from pydantic import BaseModel
import psycopg2
from typing import List, Annotated, Optional
import crud
from db_main import engine, SessionLocal
from sqlalchemy.orm import Session
import auth
from auth import get_current_user
import httpx, os
from dotenv import load_dotenv

app = FastAPI()
app.include_router(auth.router)
security = HTTPBearer()

load_dotenv()

crud.models.Base.metadata.create_all(bind=engine)
OTHER_SERVER_URL = os.getenv("AI_SERVER_URL")

async def forward_image(file: UploadFile, token: str):
    await file.seek(0)  # Ensure file pointer is at start
    async with httpx.AsyncClient() as client:
        return await client.post(
            OTHER_SERVER_URL,
            files={"file": (file.filename, file.file, file.content_type)},
            headers={"Authorization": f"Bearer {token}"}
        )

@app.post("/upload/")
async def upload_image(token: str, file: UploadFile = File()):
    """
    Receives image and optionally a token, forwards to external server.
    """
    # Use either client-provided token or server-configured token
    forward_token = token
    
    try:
        response = await forward_image(file, forward_token)
        response.raise_for_status()
        return {"status": "success", "response": response.json()}
    except httpx.HTTPStatusError as e:
        return {"error": f"Server error: {e.response.text}", "code": e.response.status_code}
    except Exception as e:
        return {"error": str(e)}
    finally:
        await file.close()

@app.post("/secure-upload/")
async def secure_upload(file: UploadFile = File(...), credentials: HTTPBearer = Depends(security)):
    """Version that uses Bearer token from Authorization header"""
    return await upload_image(file=file, token=credentials.credentials)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


@app.get("/", status_code=status.HTTP_200_OK)
async def user(user: user_dependency, db: db_dependency):
    print(user)
    if user is None:
        raise HTTPException(status_code=401, detail='auth failed')
    return {"User": user}


@app.get("/parking_lots/{parking_lot_id}")
async def read_parking_lot_endpoint(parking_lot_id: int, db: db_dependency):
    result = crud.read_parking_lot(parking_lot_id=parking_lot_id, db=db)
    if not result:
        raise HTTPException(status_code=404, detail="parking lot is not found")
    return result

@app.get("/parking_lots")
async def read_all_parking_lots_endpoint(db: db_dependency):
    result = crud.read_all_parking_lots(db)
    if not result:
        raise HTTPException(status_code=404, detail="no parking lots found")
    return result

@app.post("/parking_lots")
async def create_parking_lot_endpoint(name: str, latitude: float, longitude: float, location_name: str, free_spots: int, capacity: int, db: db_dependency, user: user_dependency):
    crud.create_parking_lot(name, latitude, longitude, location_name, free_spots, capacity, db)

@app.post("/parking_lots/{parking_lot_id}")
async def update_parking_lot_endpoint(parking_lot_id: int, name: str, latitude: float, longitude: float, location_name: str, free_spots: int, capacity: int, db: db_dependency, user: user_dependency):
    result = crud.update_parking_lot(parking_lot_id, name, latitude, longitude, location_name, free_spots, capacity, db)
    if not result:
        raise HTTPException(status_code=404, detail="parking lot is not found")
    return result

@app.delete("/parking_lots/{parking_lot_id}")
async def delete_parking_lot_endpoint(parking_lot_id: int, db: db_dependency, user: user_dependency):
    result = crud.delete_parking_lot(parking_lot_id=parking_lot_id, db=db)
    if not result:
        raise HTTPException(status_code=404, detail="parking lot is not found")
    return result


@app.get("/cameras/{camera_id}")
async def read_camera_endpoint(camera_id: int, db: db_dependency):
    result = crud.read_cameras(camera_id=camera_id, db=db)
    if not result:
        raise HTTPException(status_code=404, detail="camera is not found")
    return result

@app.get("/cameras")
async def read_all_cameras_endpoint(db: db_dependency):
    result = crud.read_all_cameras(db)
    if not result:
        raise HTTPException(status_code=404, detail="no cameras found")
    return result

@app.post("/cameras")
async def create_camera_endpoint(name: str, parking_lot_id: int, api: str, config, db: db_dependency, user: user_dependency):
    crud.create_camera(name,  parking_lot_id, api, config, db)

@app.post("/cameras/{camera_id}")
async def update_camera_endpoint(camera_id: int, name: str, parking_lot_id: int, api: str, config, db: db_dependency, user: user_dependency):
    result = crud.update_camera(camera_id, name, parking_lot_id, api, config, db)
    if not result:
        raise HTTPException(status_code=404, detail="camera is not found")
    return result

@app.delete("/cameras/{camera_id}")
async def delete_camera_endpoint(camera_id: int, db: db_dependency, user: user_dependency):
    result = crud.delete_camera(camera_id=camera_id, db=db)
    if not result:
        raise HTTPException(status_code=404, detail="camera is not found")
    return result
