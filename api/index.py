# Vercel entrypoint: Vercel looks for an ASGI `app` in api/*.py
from backend.app import app  # noqa: F401
