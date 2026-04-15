from prometheus_fastapi_instrumentator import Instrumentator
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, HttpUrl
from sqlalchemy import create_engine, Column, String
from sqlalchemy.orm import declarative_base, sessionmaker
import aiohttp
import os

app = FastAPI()

Instrumentator().instrument(app).expose(app)

# DATABASE CONFIG
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise Exception("DATABASE_URL is not set")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# TABLE MODEL
class URL(Base):
    __tablename__ = "urls"
    id = Column(String, primary_key=True, index=True)
    original_url = Column(String, nullable=False)

# CREATE TABLE
Base.metadata.create_all(bind=engine)

# REQUEST MODEL
class URLRequest(BaseModel):
    url: HttpUrl

# SHORTEN URL
@app.post("/", status_code=status.HTTP_201_CREATED)
def shorten_url(request: URLRequest):
    db = SessionLocal()

    try:
        count = db.query(URL).count() + 1
        short_id = str(count)

        new_url = URL(id=short_id, original_url=str(request.url))
        db.add(new_url)
        db.commit()

        return {"short_url": f"http://localhost:8000/{short_id}"}
    
    finally:
        db.close()

# REDIRECT TO ORIGINAL
@app.get("/{short_id}")
def redirect_to_original(short_id: str):
    db = SessionLocal()

    try:
        url = db.query(URL).filter(URL.id == short_id).first()

        if not url:
            raise HTTPException(status_code=404, detail="URL not found")

        return RedirectResponse(url=url.original_url)
    
    finally:
        db.close()

# ASYNC EXTERNAL API
@app.get("/fetch-data")
async def fetch_external_data():
    async with aiohttp.ClientSession() as session:
        async with session.get("https://jsonplaceholder.typicode.com/todos/1") as response:
            if response.status != 200:
                raise HTTPException(status_code=502, detail="External API error")
            return await response.json()
