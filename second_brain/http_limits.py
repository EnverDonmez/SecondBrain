"""Bound bytes before JSON or multipart parsing consumes the request."""

from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class RequestSizeLimit:
    def __init__(self, app: ASGIApp, limit: int):
        self.app, self.limit = app, limit

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        lengths = [value for name, value in scope["headers"] if name.lower() == b"content-length"]
        if len(lengths) > 1 or (lengths and (not lengths[0].isdigit() or len(lengths[0]) > 20)):
            await JSONResponse({"error": "Invalid Content-Length"}, status_code=400)(scope, receive, send)
            return
        if lengths and int(lengths[0]) > self.limit:
            await JSONResponse({"error": "Request too large"}, status_code=413)(scope, receive, send)
            return
        total = 0

        async def bounded_receive() -> Message:
            nonlocal total
            message = await receive()
            if message["type"] == "http.request":
                total += len(message.get("body", b""))
                if total > self.limit:
                    raise HTTPException(status_code=413, detail="Request too large")
            return message

        await self.app(scope, bounded_receive, send)
