import os
from app.core.config import setup_langsmith_env
setup_langsmith_env()
from operator import itemgetter
import shutil
from app.core.config import settings
import uuid
from typing import Optional, cast
from fastapi import UploadFile
from langchain_unstructured import UnstructuredLoader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI
from langchain_community.chat_message_histories import SQLChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from pydantic import SecretStr
from app.core.database import Message, SessionLocal
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import BaseMessage
from langchain_community.vectorstores.utils import filter_complex_metadata #type: ignore
from typing import Dict
from langchain.schema.runnable import RunnableSerializable


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

    def get_session_history(self, session_id: str, limit: int = 4):
        """Get chat message history for a session"""
        return LimitedSQLChatMessageHistory(
            session_id=session_id,
            connection=settings.SQLALCHEMY_DATABASE_URL,
            limit=limit
        )

    async def upload_documents(self, files: list[UploadFile]) -> list[str]:
        processed_files: list[str] = []   
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        
        allowed_extensions = (
            ".bmp", ".csv", ".doc", ".docx", ".eml", ".epub", ".heic",
            ".html", ".jpeg", ".png", ".md", ".msg", ".odt", ".org",
            ".p7s", ".pdf", ".ppt", ".pptx", ".rst", ".rtf", ".tiff",
            ".txt", ".tsv", ".xls", ".xlsx", ".xml"
        )

        for file in files:
            if not file.filename or not file.filename.endswith(allowed_extensions):
                continue
            
            upload_path = os.path.join(settings.UPLOAD_DIR, file.filename)
            
            with open(upload_path, "wb") as f:
                shutil.copyfileobj(file.file, f)
            
            chunks = UnstructuredLoader(upload_path).load_and_split(self.text_splitter)
            chunks = filter_complex_metadata(chunks)
            
            await self.vector_store.aadd_documents(chunks)
            processed_files.append(file.filename)
        
        return processed_files
    
    def query_document(self, question: str, session_id: Optional[str] = None) -> str:
        if not session_id:
            session_id = str(uuid.uuid4())
        
        retriever = self.vector_store.as_retriever(
            search_kwargs={"k": 3}
        )

        prompt = ChatPromptTemplate.from_messages([ #type: ignore
            ("system", "You are a helpful assistant. Answer questions based on the provided context if it exists. If you don't know the answer, just say that you don't know, don't try to make up an answer. Answer in a concise manner."),
            MessagesPlaceholder(variable_name="history"),
            ("human", "Context: {context}, question: {input}"),
        ])
        
        # Create retrieval chain
        retrieval_chain = cast(
            RunnableSerializable[Dict[str, str], str],
            (
                {
                    "context": itemgetter("input") | retriever | format_docs,
                    "input": itemgetter("input"),
                    "history": itemgetter("history"),
                }
                | prompt
                | self.llm
                | StrOutputParser()
            )
        )
                
        # Wrap with message history
        chain_with_history = RunnableWithMessageHistory(
            retrieval_chain,
            self.get_session_history,
            input_messages_key="input",
            history_messages_key="history",
        )

        result = chain_with_history.invoke( # type: ignore
            {"input": question},
            config={"configurable": {"session_id": session_id}}
        )
        
        return cast(str,result)

    def clear_chat_history(self, session_id: str) -> bool:
        """Clear chat history for a specific session"""
        history = self.get_session_history(session_id)
        history.clear()
        return True

    def get_all_sessions(self) -> list[str]:
        """Get all unique session IDs from LangChain's message store"""
        from sqlalchemy import create_engine, text
        
        # SQL logging already enabled here
        engine = create_engine("sqlite:///./db.sqlite", echo=True)
        
        with engine.connect() as conn:
            query = text("SELECT DISTINCT session_id FROM message_store")
            result = conn.execute(query)
            return [row[0] for row in result.fetchall()]
        
class LimitedSQLChatMessageHistory(SQLChatMessageHistory):
    def __init__(self, session_id: str, connection: str, limit: int = 5):
        super().__init__(session_id, connection)
        self.limit = limit

    @property
    def messages(self) -> list[BaseMessage]:  # type: ignore[override]
        """Retrieve the last N messages from db using ORM style"""
        with SessionLocal() as session:
            result = (
                session.query(Message)
                .filter(Message.session_id == self.session_id)
                .order_by(Message.id.desc())
                .limit(self.limit)
                .all()
            )
            
            messages: list[BaseMessage] = []
            for record in result:
                # Use the converter to convert from SQL model to BaseMessage
                message = self.converter.from_sql_model(record)
                messages.append(message)
            
            return messages

def format_docs(docs: list[Document]):
    return "\n\n".join([doc.page_content for doc in docs])