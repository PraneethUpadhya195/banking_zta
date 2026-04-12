import sys
import os

# Link to shared folder
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'shared')))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

# Import all your routers
from routes import router as transfer_router
from auth_routes import router as auth_router
from admin_routes import router as admin_router
from account_routes import router as account_router

app = FastAPI(title="Zero Trust Core Banking")

'''
# CORS for React
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)'''

@app.middleware("http")
async def audit_middleware(request: Request, call_next):
    # You can add global request logging here later if needed
    response = await call_next(request)
    return response

# Plug in the microservice logic!
app.include_router(transfer_router)
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(account_router)