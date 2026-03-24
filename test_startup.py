"""Test startup."""
import asyncio
import traceback
import sys

async def test_startup() -> None:
    try:
        from budgie.main import lifespan, app  # noqa: PLC0415
        async with lifespan(app):
            print("STARTUP OK", flush=True)
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        sys.exit(1)

asyncio.run(test_startup())
print("DONE")
