import uvicorn
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from controllers.getNearesPost import getNearesPost
from database import engine, get_db
from sqlalchemy.orm import Session


app = FastAPI(debug=True)

origins = [
    "http://localhost:5174",
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


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)