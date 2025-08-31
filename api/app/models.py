from pydantic import BaseModel
from typing import List

class QueryRequest(BaseModel):
    question: str
    document_name: str

class QueryResponse(BaseModel):
    answer: str

class UploadResponse(BaseModel):
    message: str
    files_processed: List[str]