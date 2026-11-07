import asyncio

from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(title="PulseBoard demo service")


@app.get("/ok")
async def ok():
    return {"status": "ok", "message": "A healthy demo endpoint"}


@app.get("/error")
async def error():
    return JSONResponse(
        {"status": "error", "message": "An intentional HTTP 500"}, status_code=500
    )


@app.get("/slow")
async def slow():
    await asyncio.sleep(65)  # Longer than even the maximum allowed total check timeout.
    return {
        "status": "ok",
        "message": "Intentionally slower than the monitoring deadline",
    }
