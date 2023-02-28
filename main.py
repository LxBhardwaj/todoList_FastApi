from fastapi import FastAPI, HTTPException, status, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
# from typing import List
from pydantic import BaseModel
import pymysql.cursors
from dotenv import load_dotenv
import os


# Load environment variables from .env file
load_dotenv()

# Initialize FastAPI
app = FastAPI()

# Initialize HTTPBasic security
security = HTTPBasic()


# Define task model
class Task(BaseModel):
    title: str
    description: str = None
    done: bool = False


# Define user model
class User(BaseModel):
    username: str
    password: str


# Define MySQL connection function
def get_db():
    connection = pymysql.connect(
        host=os.getenv('MYSQL_HOST'),
        user=os.getenv('MYSQL_USER'),
        password=os.getenv('MYSQL_PASSWORD'),
        db=os.getenv('MYSQL_DB'),
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )
    try:
        yield connection
    finally:
        connection.close()


# Define authentication function
def authenticate_user(db, credentials: HTTPBasicCredentials):
    user = get_user(db, credentials.username)
    if not user:
        return False
    if credentials.password != user['password']:
        return False
    return True


# Define user CRUD functions
def create_user(db, user: User):
    with db.cursor() as cursor:
        sql = "INSERT INTO users (username, password) VALUES (%s, %s)"
        cursor.execute(sql, (user.username, user.password))
        db.commit()
        user.id = cursor.lastrowid
        return user


def get_user(db, username: str):
    with db.cursor() as cursor:
        sql = "SELECT * FROM users WHERE username = %s"
        cursor.execute(sql, (username,))
        return cursor.fetchone()


# Define task CRUD functions
def create_task(db, task: Task, user_id: int):
    with db.cursor() as cursor:
        sql = "INSERT INTO tasks (title, description, done, user_id) VALUES (%s, %s, %s, %s)"
        cursor.execute(sql, (task.title, task.description, task.done, user_id))
        db.commit()
        task.id = cursor.lastrowid
        return task


def get_tasks(db, user_id: int):
    with db.cursor() as cursor:
        sql = "SELECT * FROM tasks WHERE user_id = %s ORDER BY created_at DESC"
        cursor.execute(sql, (user_id,))
        return cursor.fetchall()


def get_task(db, task_id: int, user_id: int):
    with db.cursor() as cursor:
        sql = "SELECT * FROM tasks WHERE id = %s AND user_id = %s"
        cursor.execute(sql, (task_id, user_id))
        return cursor.fetchone()


def update_task(db, task_id: int, task: Task, user_id: int):
    with db.cursor() as cursor:
        sql = "UPDATE tasks SET title = %s, description = %s, done = %s WHERE id = %s AND user_id = %s"
        cursor.execute(sql, (task.title, task.description, task.done, task_id, user_id))
        db.commit()
        task.id = task_id
        return task


def delete_task(db, task_id: int, user_id: int):
    with db.cursor() as cursor:
        sql = "DELETE FROM tasks WHERE id = %s AND user_id = %s"
        cursor.execute(sql, (task_id, user_id))
        db.commit()


def delete_user_tasks(db, user_id: int):
    with db.cursor() as cursor:
        sql = "DELETE FROM tasks WHERE user_id = %s"
        cursor.execute(sql, (user_id,))
        db.commit()


def delete_user(db, user_id: int):
    with db.cursor() as cursor:
        delete_user_tasks(db, user_id)
        sql = "DELETE FROM users WHERE id = %s"
        cursor.execute(sql, (user_id,))
        db.commit()


# Define API routes
@app.get("/")
async def root():
    return {"message": "This is a Todo List using FastApi"}


# Route to create a new user
@app.post("/users")
async def create_new_user(user: User, db=Depends(get_db)):
    create_user(db, user)
    return {"message": "User created successfully"}


# Route to create a new task
@app.post("/tasks")
async def create_new_task(task: Task, credentials: HTTPBasicCredentials = Depends(security), db=Depends(get_db)):
    user_id = get_user(db, credentials.username)['id']
    create_task(db, task, user_id)
    return {"message": "Task created successfully"}

# Route to get all tasks for a user
@app.get("/tasks")
async def get_all_tasks(credentials: HTTPBasicCredentials = Depends(security), db=Depends(get_db)):
    user_id = get_user(db, credentials.username)['id']
    tasks = get_tasks(db, user_id)
    return tasks

# Route to get a single task for a user
@app.get("/tasks/{task_id}")
async def get_single_task(task_id: int, credentials: HTTPBasicCredentials = Depends(security), db=Depends(get_db)):
    user_id = get_user(db, credentials.username)['id']
    task = get_task(db, task_id, user_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task

# Route to update a task
@app.put("/tasks/{task_id}")
async def update_task_details(task_id: int, task: Task, credentials: HTTPBasicCredentials = Depends(security), db=Depends(get_db)):
    user_id = get_user(db, credentials.username)['id']
    updated_task = update_task(db, task_id, task, user_id)
    if not updated_task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return {"message": "Task updated successfully"}

# Route to delete a task
@app.delete("/tasks/{task_id}")
async def delete_task_details(task_id: int, credentials: HTTPBasicCredentials = Depends(security), db=Depends(get_db)):
    user_id = get_user(db, credentials.username)['id']
    # deleted_task = delete_task(db, task_id, user_id)
    delete_task(db, task_id, user_id)
    # if not deleted_task:
    #     raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return {"message": "Task deleted successfully"}

# Route to delete all tasks for a user
@app.delete("/tasks")
async def delete_all_tasks(credentials: HTTPBasicCredentials = Depends(security), db=Depends(get_db)):
    user_id = get_user(db, credentials.username)['id']
    delete_user_tasks(db, user_id)
    return {"message": "All tasks deleted successfully"}

# Route to delete a user and all their tasks
@app.delete("/users")
async def delete_user_and_tasks(credentials: HTTPBasicCredentials = Depends(security), db=Depends(get_db)):
    user_id = get_user(db, credentials.username)['id']
    delete_user(db, user_id)
    return {"message": "User and all tasks deleted successfully"}
