from operator import itemgetter
import shutil
import os
import uuid
from typing import Optional, List
from fastapi import UploadFile
from langchain_community.document_loaders import PyPDFLoader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI
from langchain_community.chat_message_histories import SQLChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from pydantic import SecretStr
from app.core.config import settings
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory, RunnablePassthrough
from langchain_openai import ChatOpenAI
from app.documents.models import ChatMessage, ChatHistoryResponse
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser

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

    def get_session_history(self, session_id: str):
        """Get chat message history for a session"""
        return LimitedSQLChatMessageHistory(
            session_id=session_id,
            connection="sqlite:///./db.sqlite",
            limit=1
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
    
    def query_document(self, question: str, session_id: Optional[str] = None) -> str:
        if not session_id:
            session_id = str(uuid.uuid4())
        
        retriever = self.vector_store.as_retriever(
            search_kwargs={"k": 3}
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful assistant. Answer questions based on the provided context. If you don't know the answer, just say that you don't know, don't try to make up an answer. Answer in a concise manner."),
            MessagesPlaceholder(variable_name="history"),
            ("human", "Context: {context}, question: {input}"),
        ])
        
        # Create retrieval chain
        retrieval_chain = (
        {
            "context": itemgetter("input") | retriever | format_docs,
            "input": itemgetter("input"),
            "history": itemgetter("history"),
        }
        | prompt
        | self.llm
        | StrOutputParser()
    )
        
        # Wrap with message history
        chain_with_history = RunnableWithMessageHistory(
            retrieval_chain,
            self.get_session_history,
            input_messages_key="input",
            history_messages_key="history",
        )

        result = chain_with_history.invoke(
            {"input": question},
            config={"configurable": {"session_id": session_id}}
        )
        
        return result

    def get_chat_history(self, session_id: Optional[str] = None, limit: int = 50) -> ChatHistoryResponse:
        """Get chat history from LangChain's message store"""
        from sqlalchemy import create_engine, text
        
        engine = create_engine("sqlite:///./db.sqlite")
        
        with engine.connect() as conn:
            if session_id:
                # Get messages for specific session
                query = text("""
                    SELECT session_id, message, type, created_at 
                    FROM message_store 
                    WHERE session_id = :session_id 
                    ORDER BY created_at DESC 
                    LIMIT :limit
                """)
                result = conn.execute(query, {"session_id": session_id, "limit": limit})
            else:
                # Get all messages
                query = text("""
                    SELECT session_id, message, type, created_at 
                    FROM message_store 
                    ORDER BY created_at DESC 
                    LIMIT :limit
                """)
                result = conn.execute(query, {"limit": limit})
            
            messages = []
            for i, row in enumerate(result.fetchall()):
                # Parse the message content (LangChain stores it as JSON)
                import json
                try:
                    message_data = json.loads(row.message)
                    content = message_data.get('content', str(message_data))
                except:
                    content = row.message
                
                messages.append(ChatMessage(
                    id=i,
                    session_id=row.session_id,
                    message=content,
                    type=row.type,
                    created_at=row.created_at
                ))
            
            # Get total count
            if session_id:
                count_query = text("SELECT COUNT(*) FROM message_store WHERE session_id = :session_id")
                total = conn.execute(count_query, {"session_id": session_id}).scalar()
            else:
                count_query = text("SELECT COUNT(*) FROM message_store")
                total = conn.execute(count_query).scalar()
            
            return ChatHistoryResponse(messages=messages, total=total or 0)

    def clear_chat_history(self, session_id: str) -> bool:
        """Clear chat history for a specific session"""
        history = self.get_session_history(session_id)
        history.clear()
        return True

    def get_all_sessions(self) -> List[str]:
        """Get all unique session IDs from LangChain's message store"""
        from sqlalchemy import create_engine, text
        
        engine = create_engine("sqlite:///./db.sqlite")
        
        with engine.connect() as conn:
            query = text("SELECT DISTINCT session_id FROM message_store")
            result = conn.execute(query)
            return [row[0] for row in result.fetchall()]
        
class LimitedSQLChatMessageHistory(SQLChatMessageHistory):
    def __init__(self, session_id: str, connection: str, limit: int = 5):
        super().__init__(session_id, connection)
        self.limit = limit
    
    @property
    def messages(self):
        """Override to return only the last N messages"""
        all_messages = super().messages
        return all_messages[-self.limit:] if len(all_messages) > self.limit else all_messages

def format_docs(docs: list[Document]):
    return "\n\n".join([doc.page_content for doc in docs])