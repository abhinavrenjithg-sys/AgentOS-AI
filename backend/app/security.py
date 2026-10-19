import asyncio, ipaddress, socket
from urllib.parse import urlparse, urljoin
import httpx

class URLPolicyError(ValueError): pass

async def check_public_url(url: str):
    p = urlparse(url)
    if p.scheme not in {"http", "https"} or not p.hostname: raise URLPolicyError("Only absolute HTTP(S) URLs are allowed")
    if p.username or p.password: raise URLPolicyError("URLs containing credentials are not allowed")
    host = p.hostname.lower()
    if host == "localhost" or host.endswith(".localhost") or host.endswith(".local"):
        raise URLPolicyError("Local network destinations are not allowed")
    try: addresses = await asyncio.to_thread(socket.getaddrinfo, host, p.port or (443 if p.scheme == "https" else 80), type=socket.SOCK_STREAM)
    except socket.gaierror: raise URLPolicyError("Hostname could not be resolved")
    for addr in {x[4][0] for x in addresses}:
        ip = ipaddress.ip_address(addr)
        if not ip.is_global: raise URLPolicyError("Private or reserved network destinations are not allowed")

async def fetch_public(url: str) -> tuple[str, str]:
    current = url
    async with httpx.AsyncClient(timeout=8, follow_redirects=False, headers={"User-Agent":"AgentOSResearch/0.1 (public page reader)"}) as client:
        for _ in range(4):
            await check_public_url(current)
            response = await client.get(current)
            if response.status_code in {301,302,303,307,308}:
                target = response.headers.get("location")
                if not target: raise URLPolicyError("Redirect did not include a destination")
                current = urljoin(current, target); continue
            response.raise_for_status()
            if len(response.content) > 1_500_000: raise URLPolicyError("Page exceeded the 1.5 MB limit")
            return current, response.text
    raise URLPolicyError("Too many redirects")
