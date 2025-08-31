from fastapi import APIRouter, Depends, HTTPException, UploadFile
from app.logging import logger
from app.models import QueryRequest, QueryResponse, UploadResponse
from app.services import DocumentService, get_document_service

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

@router.post("/ask", response_model=QueryResponse)
async def query_doc(
    request: QueryRequest,
    doc_service: DocumentService = Depends(get_document_service)
):
    """
    Give LLM a query that will used the specified document as context
    """

    try:
        answer = doc_service.query_document(
            request.question, 
            request.document_name
        )
        return QueryResponse(answer=answer)
    except Exception as e:
        logger.error(e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An error occurred while querying the LLM"
        )

@router.get("/history")
async def get_history():
    """
    Get all chat history
    """

    return