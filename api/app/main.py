from fastapi.concurrency import asynccontextmanager
import uvicorn
from fastapi import FastAPI
from app.core.database import Base, engine
from app.documents.router import router
from app.auth.router import router as auth_router
from app.core.dependencies import initialize_ml_components

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create database tables
    Base.metadata.create_all(bind=engine)
    
    # Initialize ML components (embeddings, vector store, etc.)
    print("Initializing ML components...")
    initialize_ml_components()
    print("ML components initialized successfully!")
    
    yield

app = FastAPI(title="Smart Document Q&A API", lifespan=lifespan)

app.include_router(router)
app.include_router(auth_router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)