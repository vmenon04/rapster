from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import audio

app = FastAPI()

# Include API routes
app.include_router(audio.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # ✅ Replace with your frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],  # ✅ Allows GET, POST, PUT, DELETE, OPTIONS
    allow_headers=["*"],  # ✅ Allows all headers
)

@app.get("/")
def root():
    return {"message": "Welcome to the Music Sharing API"}