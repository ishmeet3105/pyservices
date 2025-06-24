import jwt
from datetime import datetime, timezone
from fastapi import HTTPException
import os
from app.config import config

async def check_auth(body,headers):
    if body.input.client_id is None:
        raise HTTPException(status_code=400, detail="Client ID is required for authorization.")
    auth_header = headers["Authorization"]

    if not auth_header:
        raise HTTPException(status_code=401, detail="User authorization code not found.")

    try:
        token = auth_header.split(" ")[1]
        data = jwt.decode(token, "joeydash", algorithms=["HS256"])

        if data.get('id') != body.input.client_id:
            raise HTTPException(status_code=401, detail="Client ID does not match the token.")

        token_expiration = 24 * 60
        current_time = datetime.now(timezone.utc).timestamp()
        token_age_minutes = (current_time - data.get("iat", 0)) / 60
        
        if token_age_minutes > token_expiration:
            raise HTTPException(status_code=401, detail="Authorization token expired.")

        
        # subspace_auth = req.headers.get("Subspace-Authorization-Code")
        # if config.get('env') != "dev":
        #     subspace_auth = req.headers.get("Subspace-Authorization-Code")
        #     if not subspace_auth or subspace_auth != "cxXXduarszV3VHg18dX48604zJf1iRHtPF4OELTV2nBQL8vueC":
        #         raise HTTPException(status_code=401, detail="Please use https://api.superflow.run.")
        
        if data.get("role") != "user":
            raise HTTPException(status_code=401, detail="User not authorized to do so.")
        
        return data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error: " + str(e))