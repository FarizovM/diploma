import uvicorn
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from controllers.getNearesPost import getNearesPost
from controllers.getPlume import generate_plume_image
from controllers.getTemperaturePlume import generate_temperature_plume
from database import engine, get_db
from sqlalchemy.orm import Session


app = FastAPI(debug=True)

origins = [
    "http://localhost:5173",
    # Add more origins here
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/neares-post")
def api_get_neares_post(x: Optional[float] = None, y: Optional[float] = None, db: Session = Depends(get_db)):
    # `getNearesPost` expects parameters (lat, len, db).
    return getNearesPost(x, y, db)

@app.get("/api/plume")
def api_get_plume(lat: float, lng: float, wind_dir: float, wind_speed: float):
    # У реальному житті ти можеш передавати лише ID станції і діставати ці дані з БД.
    # Для прикладу ми приймаємо їх прямо з фронтенду.
    return generate_plume_image(lat, lng, wind_dir, wind_speed)

@app.get("/api/temperature-plume")
def api_get_temp_plume(lat: float, lng: float, wind_dir: float, wind_speed: float, air_temp: float, bg_temp: float ):
    return generate_temperature_plume(lat, lng, wind_dir, wind_speed, air_temp, bg_temp)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)