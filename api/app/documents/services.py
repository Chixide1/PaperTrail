import shutil
import os
from fastapi import UploadFile
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.chains import RetrievalQA
from langchain_openai import ChatOpenAI
from pydantic import SecretStr
from app.core.config import settings

class DocumentService:
    def __init__(self) -> None:
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )

        self.vector_store = Chroma(
            persist_directory=settings.CHROME_DIR,
            embedding_function=self.embeddings
        )

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )

        self.llm = ChatOpenAI(
            api_key=SecretStr(settings.OPENAI_KEY), 
            streaming=True
        )

    async def upload_documents(self, files: list[UploadFile]) -> list[str]:
        processed_files: list[str] = []   
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        
        for file in files:
            if not file.filename or not file.filename.endswith(".pdf"):
                continue
                
            upload_path = os.path.join(settings.UPLOAD_DIR, file.filename)
            
            with open(upload_path, "wb") as f:
                shutil.copyfileobj(file.file, f)
            
            pdf_chunks = PyPDFLoader(upload_path).load_and_split(self.text_splitter)
            
            for i, chunk in enumerate(pdf_chunks):
                chunk.metadata.update({ # type: ignore
                    "source": file.filename,
                    "chunk_id": i,
                    "total_chunks": len(pdf_chunks)
                })
            
            await self.vector_store.aadd_documents(pdf_chunks)
            processed_files.append(file.filename)
        
        return processed_files
    
    def query_document(self, question: str, document_name: str) -> str:
        retriever = self.vector_store.as_retriever(
            search_kwargs={
                "k": 5,
                "filter": {"source": document_name}
            }
        )
        
        qa_chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            retriever=retriever,
            return_source_documents=False
        )
        
        result = qa_chain({"query": question})
        return result["result"]
    
def get_document_service():
    return DocumentService()