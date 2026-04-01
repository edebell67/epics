import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import controlRoutes, conversionRoutes, subscriberRoutes
from .scripts.init_database import initialize_database

app = FastAPI(
    title="Strategy Warehouse Marketing Engine API",
    description="Backend API for capturing subscriber intent and preferences.",
    version="0.1.2",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:3001", "http://localhost:3001", "http://127.0.0.1:3000", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(subscriberRoutes.router)
app.include_router(conversionRoutes.router)
app.include_router(controlRoutes.router)


@app.on_event("startup")
def startup() -> None:
    initialize_database(seed=True)


@app.get("/")
def root():
    return {"message": "Strategy Warehouse Marketing Engine API is running"}


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
