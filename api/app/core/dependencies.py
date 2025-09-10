from fastapi import Depends
from sqlalchemy.orm import Session
from app.auth.services import UserService
from app.documents.services import DocumentService
from app.core.database import SessionLocal
from app.core.security import oauth2_scheme
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.core.config import settings

# Global variables to store initialized instances
_embeddings = None
_vector_store = None
_text_splitter = None

def initialize_ml_components():
    """Initialize ML components once at startup"""
    global _embeddings, _vector_store, _text_splitter
    
    print("Initializing embeddings...")
    _embeddings = HuggingFaceEmbeddings()
    
    print("Initializing vector store...")
    _vector_store = Chroma(embedding_function=_embeddings, persist_directory=settings.CHROME_DIR)
    
    print("Initializing text splitter...")
    _text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
    )
    
    print("ML components initialization complete!")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_user_service(db: Session = Depends(get_db)):
    from app.auth.services import UserService
    return UserService(db)

def get_current_user(
    token: str = Depends(oauth2_scheme),
    user_svc: UserService = Depends(get_user_service)
):
    """Dependency to verify & get current user from access token"""
    return user_svc.verify_access_token(token)

def get_vector_store():
    """Get the pre-initialized vector store"""
    if _vector_store is None:
        raise RuntimeError("Vector store not initialized. Make sure FastAPI lifespan is properly configured.")
    return _vector_store

def get_text_splitter():
    """Get the pre-initialized text splitter"""
    if _text_splitter is None:
        raise RuntimeError("Text splitter not initialized. Make sure FastAPI lifespan is properly configured.")
    return _text_splitter

def get_document_service(
        db: Session = Depends(get_db),
        vector_store: Chroma = Depends(get_vector_store),
        text_splitter: RecursiveCharacterTextSplitter = Depends(get_text_splitter)
    ):
    return DocumentService(db, vector_store, text_splitter)