# SPDX-License-Identifier: Apache-2.0
import uvicorn

from overlord.config import Settings


def main() -> None:
    settings = Settings()
    uvicorn.run(
        "overlord.api:create_app",
        factory=True,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        access_log=False,
    )
