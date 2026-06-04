import os
from fastapi import HTTPException
from fastapi.responses import FileResponse

STORAGE_DIR = "document_storage"

def fetchFromDB(doc_id: str) -> FileResponse:
    file_name = f"{doc_id}.pdf"
    file_path = os.path.join(STORAGE_DIR, file_name)
    
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404, 
            detail=f"Document storage asset '{file_name}' does not exist on this server."
        )
        
    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=file_name,
        content_disposition_type="inline"
    )