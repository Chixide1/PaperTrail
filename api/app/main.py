import uvicorn
from fastapi import FastAPI
from app.documents.router import router
from app.auth.router import router as auth_router

app = FastAPI(title="Smart Document Q&A API")

app.include_router(router)
app.include_router(auth_router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)