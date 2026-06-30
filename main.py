from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import List
from pwdlib import PasswordHash
from jose import jwt, JWTError, ExpiredSignatureError
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from database import engine, get_db
from models import Base, ItemModel, UserModel


# Instantiate FastAPI instance
app = FastAPI()

Base.metadata.create_all(bind=engine)

SECRET_KEY = 'supersecretkey'
ALGORITHM = 'HS256'
TOKEN_EXPIRE = 10*60
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login", auto_error=False)

# token = jwt.encode(
#     {'sub': 'chan'},
#     SECRET_KEY,
#     algorithm=ALGORITHM
# )

# print(token)

# payload = jwt.decode(
#     token,
#     SECRET_KEY,
#     algorithms=[ALGORITHM]
# )

# print(payload)


# Define a mock up database 
# user_db = {}


# Password hashing
password_hash = PasswordHash.recommended()


# Pydantic model or Request/Response model for user
class UserRegister(BaseModel):
    username: str
    password: str

# class UserLogin(BaseModel):
#     username: str
#     password: str

class UserResponse(BaseModel):
    username: str


# item_db = {
#     1: {"id": 1, "name": "test1"},
#     2: {"id": 2, "name": "test2"}
# }

# item_db_counter = 1


# Pydantic model or Request/Response model for item
class ItemResponse(BaseModel):
    id: int
    name: str


class Item(BaseModel):
    name: str





# helpers
def hash_password(password: str):
    return password_hash.hash(password)

def verify_password(password: str, hashed_password: str):
    return password_hash.verify(password, hashed_password)

# Auth endpoints
@app.post("/register")
def register(
    user: UserRegister,
    db: Session = Depends(get_db)
):
    db_user = (
        db.query(UserModel).filter(UserModel.username == user.username).first()
    )

    if db_user:
        raise HTTPException(400, "User already exists.")
    
    new_user = UserModel(
        username=user.username,
        password=hash_password(user.password)
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


# Authorization Endpoint
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Please login first"
        )

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )
        
    except ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except JWTError:
        raise HTTPException(401, "Invalid token")
    except:
        raise HTTPException(401, "Invalid token")
    
    username = payload.get("sub")

    if not username:
        raise HTTPException(401, "Invalid token")

    user = (
        db.query(UserModel).filter(UserModel.username == username).first()
    )

    if not user:
        raise HTTPException(401, "User not found")

    return user


@app.get("/users", response_model=List[UserResponse])
def get_users(
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
    ):
    return db.query(UserModel).all()


@app.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):

    db_user = db.query(UserModel).filter(UserModel.username == form_data.username).first()

    if not db_user:
        raise HTTPException(401, "Invalid credentials")
    
    if not verify_password(form_data.password, db_user.password):
        raise HTTPException(401, "Invalid credentials")
    
    expire = datetime.now(timezone.utc) + timedelta(seconds=TOKEN_EXPIRE)
    
    token = jwt.encode(
        {
            'sub': form_data.username,
            'exp': expire
        },
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    return {
        "access_token": token,
        "token_type": "bearer"
    }

@app.get("/me", response_model=UserResponse)
def get_me(current_user: UserModel = Depends(get_current_user)):
    return current_user


@app.get("/")
def home():
    return {"message": "Hello world"}



# Create CRUD endpoints
# C - Create - post
# R - Read - get
# U - Update - put/patch sometime post
# D - Delete - delete


# Read 
@app.get("/item", response_model=List[ItemResponse])
def get_item(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return db.query(ItemModel).all()

# Create
@app.post("/item/new", response_model=ItemResponse)
def new_item(
    item: Item, 
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_item = ItemModel(name=item.name)

    db.add(db_item)
    db.commit()
    db.refresh(db_item)

    return db_item

# Update
@app.put("/item/{item_id}", response_model=ItemResponse)
def update_item(
    item_id: int, 
    item: Item, 
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_item = db.query(ItemModel).filter(ItemModel.id == item_id).first()

    if not db_item:
        raise HTTPException(404, "Item not found")

    db_item.name = item.name

    db.commit()
    db.refresh(db_item)

    return db_item


# Delete
@app.delete("/item/{item_id}", response_model=ItemResponse)
def delete_item(
    item_id: int, 
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_item = db.query(ItemModel).filter(ItemModel.id == item_id).first()

    if not db_item:
        raise HTTPException(404, "Item not found")
    
    db.delete(db_item)
    db.commit()

    return db_item


