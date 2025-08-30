from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session
from passlib.context import CryptContext
import models, database
import os

app = FastAPI()
templates = Jinja2Templates(directory='templates')
models.Base.metadata.create_all(bind=database.engine)
app.add_middleware(SessionMiddleware, secret_key="your_secret_key_here")

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()


pwd_context = CryptContext(schemes=["bcrypt"],deprecated = "auto")

def hash_password(password:str):
    return pwd_context.hash(password)
def verify_password(plain_password,hashed_password):
    return pwd_context.verify(plain_password,hashed_password)

    
Blogs = []
@app.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    if "user" not in request.session:
        return RedirectResponse("/signup")

    user = db.query(models.User).filter(models.User.username == request.session["user"]).first()
    blogs = db.query(models.Blog).filter(models.Blog.user_id == user.id).all()
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "blogs": blogs,
        "user": user.username
    })

@app.get("/signup")
def signup_form(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})

@app.get("/login")
def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/add")
def show_blog(request:Request):
    return templates.TemplateResponse("add_blog.html",{"request":request})

@app.post("/add")
def add_blog(
    request: Request,
    title: str = Form(...),
    content: str = Form(...),
    db: Session = Depends(get_db)
):
    if "user" not in request.session:
        return RedirectResponse("/login", status_code=303)
    
    user = db.query(models.User).filter(models.User.username == request.session["user"]).first()
    if not user:
        return RedirectResponse("/signup?error=Please signup first", status_code=303)

    new_blog = models.Blog(title=title, content=content, user_id=user.id)
    db.add(new_blog)
    db.commit()

    return RedirectResponse("/", status_code=303)

@app.post("/delete/{blog_id}")
def delete_blog(blog_id:int,db:Session=Depends(get_db)):
    blog = db.query(models.Blog).filter(models.Blog.id == blog_id).first()
    if blog:
        db.delete(blog)
        db.commit()
    return RedirectResponse("/",status_code=303)

@app.get("/edit/{blog_id}")
def edit_blog(request:Request,blog_id:int,db:Session=Depends(get_db)):
    blog = db.query(models.Blog).filter(models.Blog.id == blog_id).first()
    if not blog:
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse("edit.html",{"request":request,"blog":blog})

@app.post("/edit/{blog_id}")
def update_blog(blog_id:int,title:str=Form(...),content:str=Form(...),db:Session=Depends(get_db)):
    blog = db.query(models.Blog).filter(models.Blog.id == blog_id).first()
    if blog:
        blog.title = title
        blog.content = content
        db.commit()
    return RedirectResponse("/",status_code=303)

@app.get("/blog/{blog_id}")
def blog_detail(request:Request,blog_id:int,db:Session=Depends(get_db)):
    blog = db.query(models.Blog).filter(models.Blog.id == blog_id).first()
    if not blog:
        return RedirectResponse("index.html",status_code=303)
    return templates.TemplateResponse("detail.html",{"request":request,"blog":blog})

@app.post("/signup")
def signup(username:str=Form(...),password:str=Form(...),db:Session=Depends(get_db)):
    existing_user = db.query(models.User).filter(models.User.username == username).first()
    if existing_user:
        return RedirectResponse("/login", status_code=303)
    hashed_pw = hash_password(password)
    user = models.User(username=username,password=hashed_pw)
    db.add(user)
    db.commit()
    db.refresh(user)
    return RedirectResponse("/login",status_code=303)

@app.post("/login")
def login(request:Request,username:str=Form(...),password:str=Form(...),db:Session=Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        return RedirectResponse("/signup", status_code=303)
    
    if not verify_password(password, user.password):
        return {"error": "Invalid Credentials"}
    request.session['user'] = username
    return RedirectResponse("/",status_code=303)

@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)

