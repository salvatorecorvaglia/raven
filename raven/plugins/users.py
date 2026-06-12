"""Logged-in users plugin."""

from __future__ import annotations

import psutil

from raven.core.models import UserInfo
from raven.plugins.base import MonitorPlugin


class UsersPlugin(MonitorPlugin):
    name = "users"
    category = "users"

    def is_available(self) -> bool:
        return True

    def collect(self) -> list[UserInfo]:
        users: list[UserInfo] = []
        seen: set[str] = set()
        for u in psutil.users():
            key = f"{u.name}:{u.terminal}"
            if key in seen:
                continue
            seen.add(key)
            users.append(
                UserInfo(
                    name=u.name,
                    terminal=u.terminal,
                    host=u.host or "",
                    started=u.started,
                )
            )
        return users
