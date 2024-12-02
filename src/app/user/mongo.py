# Requirements:
# pip install fastapi uvicorn motor pydantic pymongo

from fastapi import FastAPI, HTTPException, Body, APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional
from bson import ObjectId
import motor.motor_asyncio

mongorouter=APIRouter()

# MongoDB Connection
class MongoDBConnection:
    def __init__(self, database_url: str = "mongodb://localhost:27017"):
        self.client = motor.motor_asyncio.AsyncIOMotorClient(database_url)
        self.db = self.client.user_database
        self.collection = self.db.users

db_connection = MongoDBConnection()


# Pydantic Model for User
class UserModel(BaseModel):
    id: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=50)
    email: str = Field(..., pattern=r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')
    age: int = Field(..., gt=0, lt=120)

    class Config:
        json_encoders = {
            ObjectId: str
        }
        schema_extra = {
            "example": {
                "name": "John Doe",
                "email": "john.doe@example.com",
                "age": 30
            }
        }
@mongorouter.post("/users", response_model=UserModel, status_code=201)
async def create_user(user: UserModel = Body(...)):
    """
    Create a new user in the database
    - Validates user input
    - Inserts user into MongoDB
    - Returns created user
    """
    user_dict = user.dict()

    user_dict.pop('id', None)

    result = await db_connection.collection.insert_one(user_dict)

    user_dict['id'] = str(result.inserted_id)

    return user_dict

@mongorouter.get("/users", response_model=List[UserModel])
async def list_users(skip: int = 0, limit: int = 10):
    """
    Retrieve list of users with optional pagination
    - Skip: Number of users to skip
    - Limit: Maximum number of users to return
    """
    users = await db_connection.collection.find().skip(skip).limit(limit).to_list(limit)
    return [UserModel(**user) for user in users]

@mongorouter.get("/users/{user_id}", response_model=UserModel)
async def get_user(user_id: str):
    """
    Retrieve a single user by their ID
    - Raises 404 if user not found
    """
    user = await db_connection.collection.find_one({"_id": ObjectId(user_id)})
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return UserModel(**user)

@mongorouter.put("/users/{user_id}", response_model=UserModel)
async def update_user(user_id: str, user: UserModel = Body(...)):
    """
    Update an existing user
    - Validates user input
    - Updates user in MongoDB
    - Returns updated user
    """
    user_dict = {k: v for k, v in user.dict().items() if v is not None}

    user_dict.pop('id', None)

    result = await db_connection.collection.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": user_dict}
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="User not found")

    updated_user = await db_connection.collection.find_one({"_id": ObjectId(user_id)})
    return UserModel(**updated_user)


@mongorouter.delete("/users/{user_id}", status_code=204)
async def delete_user(user_id: str):
    """
    Delete a user by their ID
    - Removes user from MongoDB
    - Returns 204 No Content on success
    """
    result = await db_connection.collection.delete_one({"_id": ObjectId(user_id)})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")

    return JSONResponse(status_code=204, content=None)

