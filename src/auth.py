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

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import firebase_admin
from firebase_admin import credentials, auth
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from sqlmodel import select, delete
from datetime import datetime, timedelta, timezone
from typing import Annotated
from models import User, UserPublic, Session
import db
from uuid import UUID
from dotenv import load_dotenv
from pwdlib.hashers.argon2 import Argon2Hasher
from sqlalchemy.exc import IntegrityError
import hashlib
import os
import secrets
import re

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
SALT = os.getenv("SALT")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

security = HTTPBearer()

def queryUserWithPhoneNumber(phoneNumber: str, db) -> UserPublic:

# Cryptographically verifying the inputted phone number against the database
    regexedPhoneNumber = re.sub(r"\D", "", phoneNumber)
    encodedPhoneNumber = regexedPhoneNumber + SALT
    toComparePhoneNumber = hashlib.sha256(encodedPhoneNumber.encode("UTF-8")).hexdigest()
    statement = select(User).where(User.phoneNumber == toComparePhoneNumber)
    query = db.exec(statement).first()

# If hit, return UUID, if not, return None
    if not query:
        return None
    return query
    
def getUser(uid: str, db) -> UserPublic:

# Querying for the user with the phone number that is hashed and salted
    statement = select(User).where(User.firebase_uid == uid)
    query = db.exec(statement).first()

# If hit, return UUID, if not, return None
    if not query:
        return None
    return query

def authorize(id_token: str, db):

# Verify id_token with the Firebase. 
# Then call getUser, verify if user exists in the database with the phone number that is hashed and salted.
    decoded = auth.verify_id_token(id_token)
    if not decoded:
        return None
    
    uid = decoded.get("uid")
    phone_number = decoded.get("phone_number")
    user = getUser(uid, db)

    if user is None:
        newUser = registerUser(firebase_uid = uid, phone_number = phone_number, db=db)
        if not newUser:
            return None
        return newUser
    
    return user

def create_access_token(data: dict, expires_delta: timedelta | None = None):

# Encoding given data
    to_encode = data.copy()

# If expire minutes set, set the "set minutes"
# If not, set 15 minutes as the default time
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)

# Encode expire into the to_encode variable
    to_encode.update({"exp": expire})

# Encode the JWT with the to_encode data, sign it with SECRET_KEY and set the algorithm, then return the JWT
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_session(uuid: str, db):

# Writing new JTI and refresh_token 
    jti = secrets.token_hex(24)
    refresh_token = secrets.token_hex(24)

# Initializing a new session as sessions could be created from different devices
    session = Session(
        uuid=uuid,
        jti=jti,
        refresh_token=refresh_token,
        is_revoked=False
    )
    
# Writing to the database
    db.add(session)
    db.commit()
    db.refresh(session)

# Returning the new JTI and refresh_token
    return jti, refresh_token

def update_session(refresh_token: str, db):

# Querying for the refresh_token in the Session table with the refresh_token parameter
    statement = select(Session).where(Session.refresh_token == refresh_token)
    res = db.exec(statement).first()

# Writing new JTI and refresh_token
    jti = secrets.token_hex(24)
    refresh_token = secrets.token_hex(24)
    
# Writing new JTI and refresh_token to the same entry that got queried with the passed refresh_token
    res.jti = jti
    res.refresh_token = refresh_token
    res.is_revoked = False
    
# Writing to the database
    db.add(res)
    db.commit()
    db.refresh(res)

# Returning the new JTI and refresh_token
    return jti, refresh_token

def verify_refresh_token(token: str, db):

# Querying for the refresh_token in the Session table with the refresh_token parameter to verify if it is there or not
    statement = select(Session).where(Session.refresh_token == token)
    res = db.exec(statement).first()

# If a hit, the refresh token is valid and good to go for assigning a new access token with a new JTI
# If not, the refresh token is either rotated or doesn't exist.
    if res:
        return res
    else:
        return None

def verify_jti(jti: str, db):

# Querying for the JTI inside Session table with the JTI parameter
    statement = select(Session).where(Session.jti == jti)
    res = db.exec(statement).first()

# If hit, session exists and good for getting the UUID.
# If no hit, session doesn't exist.
    if res:
        return res
    else:
        return None

async def get_current_user(credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)], db: db.SessionDep) -> UserPublic:

    token = credentials.credentials

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        jti = payload.get("jti")
        if jti is None:
            raise credentials_exception
    except InvalidTokenError:
        raise credentials_exception
    
# Verifying JWT and grabbing the UUID from the Session table.
    user = verify_jti(payload.get("jti"), db)

# If returned, return the JWT owner user ID
# If not, return HTTP 401
    if user is None:
        raise credentials_exception
    return user.uuid

def registerUser(firebase_uid: str, phone_number: str, db) -> UserPublic:
    with db as db:
        try:
        # Hashing and salting phone number
            regexedPhoneNumber = re.sub(r"\D", "", phone_number)
            encodedPhoneNumber = regexedPhoneNumber + SALT
            hashedPhoneNumber = hashlib.sha256(encodedPhoneNumber.encode("UTF-8")).hexdigest()

            user = User(firebase_uid=firebase_uid, phoneNumber=hashedPhoneNumber)
        
        # Writing to the database
            db.add(user)
            db.commit()
            db.refresh(user)
        
        # Returning new user
            return user
                
        except IntegrityError as e:
            db.rollback()
            return None