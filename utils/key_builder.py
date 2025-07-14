from typing import Any, Awaitable, Callable, Dict, Tuple, Union
from fastapi import Request, Response


def no_auth_header_key_builder(
    func: Callable,
    namespace: str = "",
    *,
    request: Request,
    response: Response,
    args: Tuple[Any, ...],
    kwargs: Dict[str, Any],
) -> Union[str, Awaitable[str]]:
    query_params = request.url.query
    return f"{namespace}:{request.url.path}?{query_params}"
