import asyncio
import aiosonic

async def check_online(timeout=1.0):
    try:
        conn = aiosonic.HTTPClient()
        resp = await asyncio.wait_for(conn.get('https://google.com', timeout=timeout), timeout=timeout)
        await conn.shutdown()
        if resp.status_code == 200:
            return True
    except Exception:
        pass
    return False
