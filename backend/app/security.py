import asyncio
import ipaddress
import socket
from urllib.parse import urljoin, urlparse

import httpx


class URLPolicyError(ValueError):
    pass


async def check_public_url(url: str):
    p = urlparse(url)
    if p.scheme not in {"http", "https"} or not p.hostname:
        raise URLPolicyError("Only absolute HTTP(S) URLs are allowed")
    if p.username or p.password:
        raise URLPolicyError("URLs containing credentials are not allowed")
    try:
        port = p.port or (443 if p.scheme == "https" else 80)
    except ValueError as exc:
        raise URLPolicyError("Invalid destination port") from exc
    host = p.hostname.lower()
    if host == "localhost" or host.endswith(".localhost") or host.endswith(".local"):
        raise URLPolicyError("Local network destinations are not allowed")
    try:
        addresses = await asyncio.to_thread(socket.getaddrinfo, host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise URLPolicyError("Hostname could not be resolved") from exc
    for addr in {x[4][0] for x in addresses}:
        ip = ipaddress.ip_address(addr)
        if not ip.is_global:
            raise URLPolicyError("Private or reserved network destinations are not allowed")


async def fetch_public(url: str) -> tuple[str, str]:
    current = url
    async with httpx.AsyncClient(
        timeout=8,
        follow_redirects=False,
        headers={"User-Agent": "AgentOSResearch/0.1 (public page reader)"},
    ) as client:
        for _ in range(4):
            await check_public_url(current)
            async with client.stream("GET", current) as response:
                if response.status_code in {301, 302, 303, 307, 308}:
                    target = response.headers.get("location")
                    if not target:
                        raise URLPolicyError("Redirect did not include a destination")
                    current = urljoin(current, target)
                    continue
                response.raise_for_status()
                content_type = (
                    response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
                )
                if content_type not in {"text/html", "application/xhtml+xml", "text/plain"}:
                    raise URLPolicyError("Source did not return an HTML or text page")
                length = response.headers.get("content-length")
                if length:
                    try:
                        declared_length = int(length)
                    except ValueError as exc:
                        raise URLPolicyError("Source returned an invalid content length") from exc
                    if declared_length < 0 or declared_length > 1_500_000:
                        raise URLPolicyError("Page exceeded the 1.5 MB limit")
                chunks = []
                size = 0
                async for chunk in response.aiter_bytes():
                    size += len(chunk)
                    if size > 1_500_000:
                        raise URLPolicyError("Page exceeded the 1.5 MB limit")
                    chunks.append(chunk)
                return current, b"".join(chunks).decode(
                    response.encoding or "utf-8", errors="replace"
                )
    raise URLPolicyError("Too many redirects")
