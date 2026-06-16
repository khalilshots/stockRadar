# backend/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Create the FastAPI app
app = FastAPI(title="Stock Radar API")

# Allow React (running on port 5173) to talk to FastAPI (running on 8000)
# Without this the browser will block all requests — this is called CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"status": "Stock Radar API is running"}

@app.get("/health")
def health_check():
    """
    Health check endpoint.
    Returns 200 OK if the API is running.
    """
    return {"status": "ok"}

