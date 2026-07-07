from typing import Annotated
from fastapi import Depends, Request
from .cache import AsyncCacheProtocol

def get_cache(request: Request) -> AsyncCacheProtocol:
    return request.app.state.cache

CacheDep = Annotated[AsyncCacheProtocol, Depends(get_cache)]
