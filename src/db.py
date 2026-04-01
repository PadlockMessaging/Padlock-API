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

from typing import Annotated
from dotenv import load_dotenv
from fastapi import Depends
from sqlmodel import Session, create_engine
import psycopg2
import os

load_dotenv()

DB = os.getenv("DB")
postgres_url = DB

connect_args = {"check_same_thread": False}
engine = create_engine(postgres_url, echo=True)

def get_session():
    with Session(engine) as session:
        yield session

SessionDep = Annotated[Session, Depends(get_session)]