#main.py
from fastapi import FastAPI
from app.routers import users, metric_discovery
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Include your routers
app.include_router(users.router, prefix="/authorization", tags=["Login & Signup"])
app.include_router(metric_discovery.router, prefix="/metric-discovery", tags=["metric discovery"])

@app.get("/")
async def root():
    return {"message": "Welcome to Othor API"}