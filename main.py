from api import statistics
from fastapi import FastAPI

app = FastAPI()
v1 = FastAPI()
v1.include_router(statistics.router)
app.mount("/v1", v1)
