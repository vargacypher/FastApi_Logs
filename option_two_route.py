from fastapi import Depends, APIRouter, Response, Request,HTMLResponse
from option_two_route import LoggingRoute


router = APIRouter(
    prefix='/auth', 
    tags=['auth'], 
    responses={
        404: {
            "Description": "Not Found !!!"
        }},
    route_class=LoggingRoute # MAGIC Happens
        )

@router.get("/login", response_class=HTMLResponse)
async def login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})
