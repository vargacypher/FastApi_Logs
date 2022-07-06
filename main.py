import logging
import time
import uuid

from fastapi import FastAPI,Request
from routes import hello2
from logging.config import dictConfig
from config import LogConfig

dictConfig(LogConfig().dict())
logger = logging.getLogger("confiapp")

app = FastAPI()
app.include_router(hello2.router)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    id = uuid.uuid4()
    logger.info(f"uuid={id} start request path={request.url.path}")
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = (time.time() - start_time) * 1000
    formatted_process_time = '{0:.2f}'.format(process_time)
    logger.info(f"uuid={id} completed_in={formatted_process_time}ms status_code={response.status_code}")
    
    return response


@app.get("/")
async def root():
    return {"message": "Hello Bigger Applications!"}
