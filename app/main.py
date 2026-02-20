from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.routes import auth, listings, purchases

app = FastAPI(title="Foundry")

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(auth.router)
app.include_router(listings.router)
app.include_router(purchases.router)
