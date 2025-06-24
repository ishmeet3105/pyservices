from pydantic import BaseModel, Field

class HeaderModel(BaseModel):
    Authorization: str
    Content_Type: str = Field(..., alias="Content-Type")

class ProspectInputModel(BaseModel):
    client_id: str
    prospect_id: str
    language:str

class ProspectRequest(BaseModel):
    input: ProspectInputModel

class postcall_request(BaseModel):
    agent_id: str
    call_id: str
    client_id: str
    is_premium: bool
    batch_size: int

class PostcallRequest(BaseModel):
    input: postcall_request