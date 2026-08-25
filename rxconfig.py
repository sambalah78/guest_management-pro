"""Reflex configuration.

Only non-secret, browser-safe configuration is exposed through Reflex config.
Server secrets are read directly from the server environment by core.config.
"""

import os

import reflex as rx
from dotenv import load_dotenv

if os.path.exists(".env"):
    load_dotenv()

config = rx.Config(
    app_name="guest_management",
    frontend_port=3000,
    backend_port=8000,
    api_url=os.getenv("API_URL", "http://localhost:8000"),
    show_reflex_badge=False,
    telemetry_enabled=True,
    env={
        "APP_URL": os.getenv("APP_URL", "http://localhost:3000"),
    },
    frontend_packages=[],
    plugins=[
        rx.plugins.SitemapPlugin(),
        rx.plugins.TailwindV4Plugin(),
        rx.plugins.RadixThemesPlugin(
            theme=rx.theme(appearance="dark", accent_color="gold")
        ),
    ],
)
