from fastapi import FastAPI, Depends, HTTPException, status, File, UploadFile, Form
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
from pathlib import Path

app = FastAPI()
app.include_router(auth.router)
security = HTTPBearer()

load_dotenv()

crud.models.Base.metadata.create_all(bind=engine)
OTHER_SERVER_URL = os.getenv("AI_SERVER_URL", "")

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]

@app.post("/receive-image")
async def receive_image(free: int, occupied:int, processing_time: int, camera_id: int, token: str, file: UploadFile = File(...)):
    try:
        image = file
        
        if not image:
            raise HTTPException(400, "No image provided")
        
        filename = os.path.basename(file.filename)
    
        # Save the file
        file_path = UPLOAD_DIR / filename

        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)
        
        return {
            "status": "success",
            "free": free,
            "occupied": occupied,
            "processing_time": processing_time,
            "camera_id": camera_id,
            "token": token,
            "file_name": filename,
            "file_path": file_path
        }
    
    except Exception as e:
        raise HTTPException(500, f"Error saving file: {str(e)}")

async def forward_image(payload: dict, file: UploadFile):
    await file.seek(0)
    async with httpx.AsyncClient() as client:
        return await client.post(
            OTHER_SERVER_URL,
            json=payload,
            files={"image": (file.filename, file.file, file.content_type)}
        )

@app.post("/upload")
async def upload_image(token: str, db: db_dependency, file: UploadFile = File(...)):
    """
    Receives image and optionally a token, forwards to external server.
    """
    # Use either client-provided token or server-configured token
    forward_token = token
    forward_id = db.query(crud.models.Cameras).filter(crud.models.Cameras.api == token).first()
    if not forward_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera with this token is not found")
    forward_id = forward_id.id
    forward_config = db.query(crud.models.Cameras).filter(crud.models.Cameras.api == token).first().config

    payload = {
        "token": forward_token,
        "camera_id": forward_id,
        "config": forward_config,
    }
    
    try:
        response = await forward_image(payload, file)
        response.raise_for_status()
        return {"status": "success", "response": response.json()}
    except httpx.HTTPStatusError as e:
        return {"error": f"Server error: {e.response.text}", "code": e.response.status_code}
    except Exception as e:
        return {"error": str(e)}
    finally:
        await file.close()


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