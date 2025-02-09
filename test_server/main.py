from fastapi import FastAPI, File, UploadFile, Depends, HTTPException
from fastapi.security import HTTPBearer

app = FastAPI()
security = HTTPBearer()

async def verify_token(credentials: HTTPBearer = Depends(security)):
    if credentials.credentials != "valid-token":
        raise HTTPException(status_code=401, detail="Invalid token")
    return credentials.credentials

@app.post("/receive-image/")
async def receive_image(
    file: UploadFile = File(...),
    token: str = Depends(verify_token)
):
    return {
        "filename": file.filename,
        "content_type": file.content_type,
        "token": token
    }