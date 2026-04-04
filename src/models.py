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

from sqlmodel import Field, SQLModel, Column
import uuid
from uuid import UUID
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from pydantic import BaseModel

class User(SQLModel, table=True):
    uuid: UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(PG_UUID(as_uuid=True), 
        primary_key=True, 
        nullable=False),
    )

    firebase_uid: str = Field(
        nullable=False, 
        unique=True
    )

    phoneNumber: str = Field(
        index=True, 
        unique=True,
        nullable=False
    )

    registrationLock: str = Field(
        nullable=True
    )

class Session(SQLModel, table=True):
    uuid: UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(PG_UUID(as_uuid=True), 
        nullable=False),
    )

    refresh_token: str = Field(
        nullable=False, 
        unique=True
    )

    jti: str = Field(
        primary_key=True,
        nullable=False,
        unique=True
    )

    is_revoked: bool = Field(
        nullable=True
    )

class UserPublic(SQLModel, table=False):
    uuid: UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(PG_UUID(as_uuid=True), 
        primary_key=True, 
        nullable=False),
    )

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str