from fastapi.concurrency import asynccontextmanager
import uvicorn
from fastapi import FastAPI
from app.core.database import Base, engine
from app.documents.router import router
from app.auth.router import router as auth_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(title="Smart Document Q&A API")

app.include_router(router)
app.include_router(auth_router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)