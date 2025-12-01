# external_attack_poc.py
# External user interaction PoC for RAG system information exfiltration.

import uvicorn
from fastapi import FastAPI, UploadFile, File, HTTPException, Response
from pydantic import BaseModel
from pathlib import Path
import shutil
import os
import json
from dotenv import load_dotenv

load_dotenv()

# --- RAG and LLM Libraries ---
# Ensure these are installed using the specific vulnerable versions.
from langchain_community.document_loaders import EverNoteLoader
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_ollama import ChatOllama
from langchain.chains import RetrievalQA

# --- Global Variables ---
# In a real system, this should be handled per-session/user.
vector_db = None
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# --- FastAPI App Initialization ---
app = FastAPI()

print("="*50)
print("Vulnerable RAG System PoC Server")
print("WARNING: This server is running with intentionally vulnerable code.")
print("="*50)

# --- API Data Models ---
class QueryRequest(BaseModel):
    question: str

# --- API Endpoints ---

@app.post("/upload")
async def upload_and_poison_knowledge_base(file: UploadFile = File(...)):
    """
    Endpoint for an external user to upload a file to create (and poison) the RAG knowledge base.
    """
    global vector_db
    
    try:
        # 1. Save the uploaded file
        file_path = UPLOAD_DIR / file.filename
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 2. [VULNERABILITY TRIGGER] Process the file with the vulnerable EverNoteLoader
        # This is where the XXE attack occurs, loading /etc/passwd instead of the file content.
        print(f"\n[!] Received '{file.filename}'. Processing with vulnerable EverNoteLoader...")
        loader = EverNoteLoader(str(file_path))
        malicious_docs = loader.load()
        print("[+] Internal file content successfully injected.")

        # 3. Poison the knowledge base
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        docs = text_splitter.split_documents(malicious_docs)
        
        # Force embeddings to use CPU to avoid CUDA errors.
        embeddings = HuggingFaceEmbeddings(
            model_name=os.getenv("EMBEDDING_MODEL_NAME"),
            model_kwargs={'device': os.getenv("EMBEDDING_DEVICE")} 
        )
        
        vector_db = FAISS.from_documents(docs, embeddings)
        print("[+] Knowledge base has been poisoned with the leaked data.")
        
        response_data = {"status": "success", "message": "Knowledge base created (and poisoned)."}
        # Manually create JSON string and add a newline for cleaner curl output
        json_string = f'{{"status":"{response_data["status"]}", "message":"{response_data["message"]}"}}\n'
        return Response(content=json_string, media_type="application/json")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/query")
async def query_llm(request: QueryRequest):
    """
    Endpoint for an external user to query the LLM and exfiltrate the poisoned information.
    """
    global vector_db
    
    if vector_db is None:
        raise HTTPException(status_code=400, detail="Knowledge base not created. Please upload a file first.")
    
    try:
        print(f"\n[?] Received query: '{request.question}'")
        # Connect to your external Ollama server
        llm = ChatOllama(
            model=os.getenv("LLM_MODEL_NAME"),
            base_url=os.getenv("LLM_BASE_URL")
        )
        
        retriever = vector_db.as_retriever()
        qa_chain = RetrievalQA.from_chain_type(llm=llm, chain_type="stuff", retriever=retriever)
        
        response = qa_chain.invoke({"query": request.question})
        result = response.get("result", "No result found.")
        
        print(f"[!] Leaked information via LLM response.")
        response_data = {"status": "success", "leaked_answer": result}
        # Manually create JSON string and add a newline for cleaner curl output
        json_string = json.dumps(response_data) + "\n"
        return Response(content=json_string, media_type="application/json")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Server Execution ---
if __name__ == "__main__":
    host = os.getenv("SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("SERVER_PORT", "8080"))
    print("\nTo run the server, use the command:")
    print(f"uvicorn external_attack_poc:app --host {host} --port {port}")
    try:
        uvicorn.run(app, host=host, port=port)
    finally:
        print()
