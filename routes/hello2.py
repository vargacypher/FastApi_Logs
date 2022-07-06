from fastapi import APIRouter

router = APIRouter()

@router.get("/test_tick/", tags=["users"])
async def read_users():
    return [{"hello": "Rick"}, {"hello": "Morty"}]

