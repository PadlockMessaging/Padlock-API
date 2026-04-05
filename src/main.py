# 
#    Padlock Messaging Project
#    Copyright (C) <2026>  <Padlock Messaging>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.

#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
#

from fastapi import FastAPI, HTTPException, Form, Request
from dataclasses import dataclass
from sqlmodel import select
from models import UserPublic
import db
from auth import *
from models import Token
from fastapi.encoders import jsonable_encoder
import firebase_admin
from firebase_admin import credentials
import os
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Create the limiter
limiter = Limiter(key_func=get_remote_address)

FIREBASE = os.getenv("FIREBASE_SECRET")
cred = credentials.Certificate(FIREBASE)
firebase_admin.initialize_app(cred)

description = """
This API is the backbone of the **Padlock Messaging Project**.

**Due to the API is not being open to the public, this documentation page will be disabled.**
"""

app = FastAPI(
    title="Padlock Messaging Project API",
    description=description,
    version="1.0.1",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@dataclass
class OAuth2RequestIdToken:
    id_token: str = Form(..., description="Your ID token")

@dataclass
class OAuth2RefreshToken:
    refresh_token: str = Form(..., description="Your refresh token")



@app.get("/api/v1/searchPhoneNumber/{phoneNumber}", tags=["Public Queries"], summary="Grab a user ID", description="*Recipient user ID is required to initiate a WebSocket. You can acquire it here.*")
async def getClientUser(phoneNumber: str, auth: Annotated[Session, Depends(get_current_user)], db: db.SessionDep) -> UserPublic:
    
# Querying for user ID
    query = getUser(phoneNumber, db)

# If hit, return queried phone number UUID, if not, return HTTP 404
    if not query:
        raise HTTPException(status_code=404, detail="User doesn't exist.")
    return query

@app.post("/auth/v1/login", tags=["Account Settings"], summary="Sign in a user", description="*Signing in of a user is handled from here.*")
async def grab_access_token(id_token: Annotated[OAuth2RequestIdToken, Depends()], db: db.SessionDep) -> Token:

# Verify credentials
    user = authorize(id_token=id_token.id_token, db=db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ID token authentication failed! Could be because of a backend issue.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
# Set access token expiration minutes
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

# Set new JTI and refresh_token
    jti, refresh_token = create_session(user.uuid, db)

# Set token_data to go in the JWT
    token_data = jsonable_encoder({
        "sub": user.uuid,
        "jti": jti,
    })

# Create access token with token_data and minutes parameter and 
# return the token with Token model containing access & refresh tokens and token_type.
    access_token = create_access_token(data=token_data, expires_delta=access_token_expires)
    return Token(access_token=access_token, refresh_token=refresh_token, token_type="bearer")

@app.post("/auth/v1/token", tags=["Account Settings"], summary="Refresh an access token", description="*Refreshing access tokens are made from here.*")
@limiter.limit("3/minute")
async def access_token_refresh(request: Request, form_data: Annotated[OAuth2RefreshToken, Depends()], db: db.SessionDep) -> Token:

# Verify refresh token
    refreshTokenUser = verify_refresh_token(form_data.refresh_token, db)
    if not refreshTokenUser:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token invalid.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
# Set access token expiration minutes
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

# Set new JTI and refresh_token
    jti, refresh_token = update_session(refreshTokenUser.refresh_token, db)
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error creating the new refresh token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
# Set token_data to go in the JWT
    token_data = jsonable_encoder({
        "sub": refreshTokenUser.uuid,
        "jti": jti
    })

# Create access token with token_data and minutes parameter and 
# return the token with Token model containing access & refresh tokens and token_type.
    access_token = create_access_token(data=token_data, expires_delta=access_token_expires)
    return Token(access_token=access_token, refresh_token=refresh_token, token_type="bearer")

@app.delete("/auth/v1/logout", tags=["Account Settings"], summary="Log out a user", description="*Logging out of a user is handled from here.*")
async def logout(auth: Annotated[Session, Depends(get_current_user)], db: db.SessionDep):
# Deleting the session with the JTI from the Session table to log out the user.
    statement = select(Session.jti).where(Session.uuid == auth)
    jti = db.exec(statement).first()
    if jti:
        statement = select(Session).where(Session.jti == jti)
        session = db.exec(statement).first()
        if session:
            db.delete(session)
            db.commit()
            return {"detail": "Successfully logged out."}
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error logging out. Session doesn't exist.",
            headers={"WWW-Authenticate": "Bearer"},
        )