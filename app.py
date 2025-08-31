# app.py  — eine einzige FastAPI-App (Agno) + statische UI
import os
import hashlib
import secrets
from fastapi import Request, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from agno.app.fastapi.app import FastAPIApp

from trainer_agent_with_tools import trainer  # dein vorhandener Agent

# --- Auth Configuration ---
EXPECTED_TOKEN = None
COOKIE_SECRET = None

def get_cookie_secret():
    global COOKIE_SECRET
    if COOKIE_SECRET is None:
        COOKIE_SECRET = os.getenv("COOKIE_SECRET", secrets.token_hex(32))
    return COOKIE_SECRET

def create_secure_token(password: str) -> str:
    secret = get_cookie_secret()
    return hashlib.sha256(f"{password}:{secret}".encode()).hexdigest()

def get_expected_token():
    global EXPECTED_TOKEN
    if EXPECTED_TOKEN is None:
        password = os.getenv("AUTH_PASSWORD")
        if password:
            EXPECTED_TOKEN = create_secure_token(password)
    return EXPECTED_TOKEN

# Agent-ID setzen, damit wir ihn per ?agent_id=... adressieren können
trainer.agent_id = "sprachtrainer"

fastapi_app = FastAPIApp(
    agents=[trainer],
    name="Sprachtrainer",
    app_id="sprachtrainer_app",
    description="Agno FastAPI App für den Sprachtrainer",
)

# 👉 Das ist unsere EINZIGE FastAPI-App
app = fastapi_app.get_app()  # Prefix default: /v1

# --- Auth Middleware ---
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    # Check if authentication is enabled
    auth_password = os.getenv("AUTH_PASSWORD")
    
    # If no AUTH_PASSWORD is set, skip authentication
    if not auth_password:
        response = await call_next(request)
        return response
    
    # Define public paths that don't require authentication
    public_paths = ["/login", "/api/login", "/favicon.ico"]
    public_static_extensions = [".css", ".js", ".png", ".ico", ".svg"]
    
    # Check if current path is public
    path = request.url.path
    if (path in public_paths or 
        any(path.endswith(ext) for ext in public_static_extensions) or
        path.startswith("/static/")):
        response = await call_next(request)
        return response
    
    # Check for valid authentication cookie
    auth_token = request.cookies.get("auth_token")
    expected_token = get_expected_token()
    
    if not auth_token or not expected_token or auth_token != expected_token:
        # Redirect to login page with return URL
        return RedirectResponse(
            url=f"/login?redirect={request.url.path}",
            status_code=302
        )
    
    # Authentication successful, proceed with request
    response = await call_next(request)
    return response

# Statische Dateien (UI)
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# --- Login Routes ---
class LoginRequest(BaseModel):
    password: str
    redirect: str = "/"

@app.get("/login")
async def login_page():
    """Serve the login HTML page."""
    return FileResponse(os.path.join(STATIC_DIR, "login.html"))

@app.post("/api/login")
async def login(request: LoginRequest):
    """Authenticate user and set secure cookie."""
    auth_password = os.getenv("AUTH_PASSWORD")
    
    if not auth_password:
        raise HTTPException(status_code=503, detail="Authentication not configured")
    
    if request.password != auth_password:
        raise HTTPException(status_code=401, detail="Invalid password")
    
    # Create secure token and set cookie
    secure_token = create_secure_token(request.password)
    
    response = RedirectResponse(
        url=request.redirect if request.redirect else "/",
        status_code=302
    )
    
    # Set secure cookie (12 months = 31536000 seconds)
    response.set_cookie(
        key="auth_token",
        value=secure_token,
        max_age=31536000,  # 12 months
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite="lax"
    )
    
    return response

@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

if __name__ == "__main__":
    # Optional auch: fastapi_app.serve(app="app:app", port=3000, reload=True)
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=3000, reload=True)
