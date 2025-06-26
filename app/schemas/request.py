from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class InputData(BaseModel):
    agent_id: str
    from_date: datetime
    to_date: datetime
    is_premium: Optional[bool] = False  # optional, defaults to False

class PostcallRequest(BaseModel):
    input: InputData

class HeaderModel(BaseModel):
    Authorization: str
    Content_Type: str = Field(..., alias="Content-Type")

class ProspectInputModel(BaseModel):
    client_id: str
    prospect_id: str
    language:str

class ProspectRequest(BaseModel):
    input: ProspectInputModel



