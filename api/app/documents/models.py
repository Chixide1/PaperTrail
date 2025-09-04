from typing import Any, Optional
from pydantic import BaseModel
from datetime import datetime

class QueryRequest(BaseModel):
    question: str
    document_name: str
    session_id: Optional[str] = None  # Add session support

class QueryResponse(BaseModel):
    answer: str
    sources: list[str] = []
    session_id: Optional[str] = None

class UploadResponse(BaseModel):
    message: str
    files_processed: list[str]

class ChatMessage(BaseModel):
    id: int
    session_id: str
    message: str
    type: str  # 'human', 'ai', or 'system'
    created_at: datetime
    
class ChatHistoryResponse(BaseModel):
    messages: list[ChatMessage]
    total: int