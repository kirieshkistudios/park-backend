from fastapi import FastAPI, Depends, HTTPException, status, File, UploadFile, Form
import json

from fastapi.responses import FileResponse
from fastapi import FastAPI, Depends, HTTPException, status, File, UploadFile
from fastapi.security import HTTPBearer
from pydantic import BaseModel
import psycopg2
from typing import List, Annotated, Optional
import crud
import models
from db_main import engine, SessionLocal
from sqlalchemy.orm import Session
import auth
from auth import get_current_user, bcrypt_context
import httpx, os
from dotenv import load_dotenv
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware

#import camparser

app = FastAPI()

# Настройка CORS
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173"
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В разработке можно использовать "*"
    allow_credentials=True,
    allow_methods=["*"],  # Разрешаем все методы
    allow_headers=["*"],  # Разрешаем все заголовки
)

app.include_router(auth.router)
security = HTTPBearer()

load_dotenv()

crud.models.Base.metadata.create_all(bind=engine)
OTHER_SERVER_URL = os.getenv("AI_SERVER_URL", "")
AI_SERVER_KEY = os.getenv("AI_SERVER_KEY", "")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")

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

@app.get("/images/{image_name}")
async def get_image(image_name: str):
    images_dir = Path("camera_snapshots")
    image_path = images_dir / f'{image_name}.png'

    # Проверяем существование файла и безопасность пути
    if not image_path.exists() or not image_path.is_file():
        raise HTTPException(status_code=404, detail="Image not found")

    # Проверяем расширение файла
    if image_path.suffix.lower() not in [".jpg", ".jpeg", ".png"]:
        raise HTTPException(status_code=400, detail="Invalid image format")

    return FileResponse(image_path)


@app.post("/receive-image")
async def receive_image(db: db_dependency, free: int = Form(...), occupied: int = Form(...),
                        processing_time: float = Form(...),
                        camera_id: int = Form(...), token: str = Form(...), image: UploadFile = File(...)):
    if os.getenv("MAIN_SERVER_KEY", "") != token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tokens didn't match")

    try:
        if not image:
            raise HTTPException(400, "No image provided")

        filename = os.path.basename(f'camera_{camera_id}.jpg')

        # Save the file
        file_path = UPLOAD_DIR / filename

        contents = await image.read()
        with open(file_path, "wb") as f:
            f.write(contents)

        cur_parking_lot_id = db.query(crud.models.Cameras).filter(crud.models.Cameras.id == camera_id).first().parking_lot_id
        cur_parking_lot = db.query(crud.models.ParkingLots).filter(crud.models.ParkingLots.id == cur_parking_lot_id).first()
        crud.update_parking_lot(cur_parking_lot_id, cur_parking_lot.name, cur_parking_lot.latitude, cur_parking_lot.longitude, cur_parking_lot.location_name, free, cur_parking_lot.capacity, db)
        
        return {
            "status": "success",
            "file_name": filename,
            "file_path": file_path
        }

    except Exception as e:
        raise HTTPException(500, f"Error saving file: {str(e)}")


async def forward_image(payload: dict, file: UploadFile):
    await file.seek(0)
    async with httpx.AsyncClient() as client:
        config_json = json.dumps(payload.get("config", {}))

        return await client.post(
            OTHER_SERVER_URL,
            data={
                "token": payload["token"],
                "camera_id": payload["camera_id"],
                "config": config_json
            },
            files={"image": (file.filename, await file.read(), file.content_type)}
        )


@app.post("/upload")
async def upload_image(db: db_dependency, token: str = Form(...), file: UploadFile = File(...)):
    """
    Receives image and optionally a token, forwards to external server.
    """
    # Use either client-provided token or server-configured token
    forward_id = db.query(crud.models.Cameras).filter(crud.models.Cameras.api == token).first()
    if not forward_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera with this token is not found")
    forward_id = forward_id.id
    forward_config = db.query(crud.models.Cameras).filter(crud.models.Cameras.api == token).first().config

    payload = {
        "token": AI_SERVER_KEY,
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


@app.get('/camscreen')
async def getscreen(url, user: user_dependency):
    return camparser.capture_video_frames(url)


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

class CreateParkRequest(BaseModel):
    name: str
    latitude: float
    longitude: float
    location_name: str
    free_spots: int
    capacity: int

class EditParkRequest(BaseModel):
    parking_lot_id: int
    name: str
    latitude: float
    longitude: float
    location_name: str
    free_spots: int
    capacity: int

@app.post("/parking_lots")
async def create_parking_lot_endpoint(createpark: CreateParkRequest, db: db_dependency, user: user_dependency):
    crud.create_parking_lot(createpark.name, createpark.latitude, createpark.longitude, createpark.location_name, createpark.free_spots, createpark.capacity, db)


@app.post("/parking_lots/{parking_lot_id}")
async def update_parking_lot_endpoint(editpark: EditParkRequest, db: db_dependency,
                                      user: user_dependency):
    result = crud.update_parking_lot(editpark.parking_lot_id, editpark.name, editpark.latitude, editpark.longitude, editpark.location_name, editpark.free_spots, editpark.capacity, db)
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


class CreateCameraRequest(BaseModel):
    name: str
    parking_lot_id: int
    api: str
    config: str

class EditCameraRequest(BaseModel):
    camera_id: int
    name: str
    parking_lot_id: int
    api: str
    config: str

@app.post("/cameras")
async def create_camera_endpoint(createcamera: CreateCameraRequest, db: db_dependency,
                                 user: user_dependency):
    crud.create_camera(createcamera.name, createcamera.parking_lot_id, createcamera.api, createcamera.config, db)


@app.post("/cameras/{camera_id}")
async def update_camera_endpoint(editcamera: EditCameraRequest, db: db_dependency,
                                 user: user_dependency):
    result = crud.update_camera(editcamera.camera_id, editcamera.name, editcamera.parking_lot_id, editcamera.api, editcamera.config, db)
    if not result:
        raise HTTPException(status_code=404, detail="camera is not found")
    return result


@app.delete("/cameras/{camera_id}")
async def delete_camera_endpoint(camera_id: int, db: db_dependency, user: user_dependency):
    result = crud.delete_camera(camera_id=camera_id, db=db)
    if not result:
        raise HTTPException(status_code=404, detail="camera is not found")
    return result


@app.get("/users")
async def read_all_users_endpoint(db: db_dependency, user: user_dependency):
    result = crud.read_all_users(db)
    if not result:
        raise HTTPException(status_code=404, detail="no users found")
    return result

@app.get("/users/{user_id}")
async def read_user_endpoint(db: db_dependency, user_id: int, user: user_dependency):
    result = crud.read_user(user_id=user_id, db=db)
    if not result:
        raise HTTPException(status_code=404, detail="user is not found")
    return result


class EditUserRequest(BaseModel):
    user_id: int
    username: str
    password: str
    is_superior: bool


@app.post("/users/{user_id}")
async def update_user_endpoint(editrequest: EditUserRequest, db: db_dependency, user: user_dependency):
    hashed_password = bcrypt_context.hash(editrequest.password)
    result = crud.update_user(editrequest.user_id, editrequest.username, hashed_password, editrequest.is_superior, db)
    if not result:
        raise HTTPException(status_code=404, detail="user is not found")
    return result

@app.delete("/users/{user_id}")
async def delete_user_endpoint(user_id: int, db: db_dependency, user: user_dependency):
    result = crud.delete_user(user_id=user_id, db=db)
    if not result:
        raise HTTPException(status_code=404, detail="user is not found")
    return result
