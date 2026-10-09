from fastapi import APIRouter
from fastapi.responses import RedirectResponse

default_page_router = APIRouter()

@default_page_router.get("/")
def default_page():
    return RedirectResponse(url="/static/chat.html")

