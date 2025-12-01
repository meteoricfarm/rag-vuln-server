#!/bin/bash

uvicorn src.external_attack_poc:app \
    --host 127.0.0.1 \
    --port 8080

curl -X POST \
    -F "file=@data/sample.enex" \
    http://127.0.0.1:8080/upload

curl -X POST \
    -H "Content-Type: application/json" \
    -d "{\"question\": \"What content is contained in the note's body\"}" \
    http://127.0.0.1:8080/query

curl -X POST \
    -F "file=@data/payload.xml" \
    http://127.0.0.1:8080/upload

curl -X POST \
    -H "Content-Type: application/json" \
    -d "{\"question\": \"What are the system user accounts listed in the document?\"}" \
    http://127.0.0.1:8080/query