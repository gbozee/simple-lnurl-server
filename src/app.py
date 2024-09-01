import os
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from .models import handler,LN_ADDRESS_DOMAIN


async def homepage(request):
    return JSONResponse({"message": "Welcome to the Node Remote API"})


def lnurlp(request: Request):
    username = request.path_params.get("username")
    encode = request.query_params.get("encode")
    user = handler.get_user(username)
    result = handler.get_ln_details(username)
    if result and user:
        if encode:
            test_callback_url = f"https://{LN_ADDRESS_DOMAIN}/lnurlp/{username}"
            return JSONResponse(
                {"ln": handler.lnurl_address_encoded(test_callback_url)}
            )
        return JSONResponse(result.dict())
    return JSONResponse(
        {
            "status": "ERROR",
            "reason": "could not process request. please try again with valid parameters",
        },
        status_code=400,
    )


def generate_invoice(request: Request): 
    amount = request.query_params.get("amount")
    username = request.path_params.get("username")
    user = handler.get_user(username)
    if amount and user:
        result = handler.generate_invoice(
            username,
            int(amount),
        )
        if result:
            return JSONResponse(result.dict())
    return JSONResponse(
        {
            "reason": "could not process request. please try again with valid parameters",
            "status": "ERROR",
        },
        status_code=400,
    )


async def health_check(request):
    return JSONResponse({"status": "healthy"})


routes = [
    Route("/", endpoint=homepage),
    Route("/health", endpoint=health_check),
    Route(
        "/lnurlp/{username}/callback",
        endpoint=generate_invoice,
        methods=["GET"],
    ),
    Route("/lnurlp/{username}", lnurlp),
    Route("/.well-known/lnurlp/{username}", lnurlp, methods=["GET"]),
]

app = Starlette(debug=True, routes=routes)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
