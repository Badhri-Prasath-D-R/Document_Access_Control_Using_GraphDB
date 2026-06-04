from pydantic import BaseModel
from typing import List

class DocumentPermission(BaseModel):
    DocumentID: str
    DocumentTitle: str
    AuthorizedByRoleCode: str

class UserAccessResponse(BaseModel):
    qtimeTaken: float
    atimeTaken: float
    psno: str
    total_accessible_documents: int
    accessible_documents: List[DocumentPermission]