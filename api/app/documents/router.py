from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, Query
from app.core.logging import logger
from app.documents.models import QueryRequest, QueryResponse, UploadResponse, ChatHistoryResponse
from app.documents.services import DocumentService
from app.core.dependencies import get_document_service

router = APIRouter()

@router.post("/upload")
async def upload_docs(
    files: list[UploadFile],
    doc_service: DocumentService = Depends(get_document_service)
):
    """
    Upload files here to be indexed and used as context for LLM
    """
    try:
        processed_files = await doc_service.upload_documents(files)
        return UploadResponse(
            message=f"Processed {len(processed_files)} files",
            files_processed=processed_files
        )
    except Exception as e:
        logger.error(e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An error occurred while trying to process the uploaded files"
        )

@router.post("/ask")
async def query_doc(
    request: QueryRequest,
    doc_svc: DocumentService = Depends(get_document_service)
):
    """
    Give LLM a query that will use the specified document as context
    """
    try:
        answer = doc_svc.query_document(
            request.question,
            request.session_id
        )
        return answer
    except Exception as e:
        logger.error(e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An error occurred while querying the LLM"
        )

@router.get("/history", response_model=ChatHistoryResponse)
async def get_history(
    session_id: Optional[str] = Query(None, description="Filter by session ID"),
    limit: int = Query(50, description="Maximum number of messages to return"),
    doc_service: DocumentService = Depends(get_document_service)
):
    """
    Get chat history, optionally filtered by session ID
    """
    try:
        return doc_service.get_chat_history(session_id=session_id, limit=limit)
    except Exception as e:
        logger.error(e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An error occurred while retrieving chat history"
        )

@router.delete("/history/{session_id}")
async def clear_session_history(
    session_id: str,
    doc_service: DocumentService = Depends(get_document_service)
):
    """
    Clear chat history for a specific session
    """
    try:
        success = doc_service.clear_chat_history(session_id)
        if success:
            return {"message": f"Chat history cleared for session {session_id}"}
        else:
            raise HTTPException(status_code=404, detail="Session not found")
    except Exception as e:
        logger.error(e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An error occurred while clearing chat history"
        )

@router.get("/sessions")
async def get_sessions(
    doc_service: DocumentService = Depends(get_document_service)
):
    """
    Get all chat session IDs
    """
    try:
        sessions = doc_service.get_all_sessions()
        return {"sessions": sessions, "total": len(sessions)}
    except Exception as e:
        logger.error(e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An error occurred while retrieving sessions"
        )