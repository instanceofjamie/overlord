# SPDX-License-Identifier: Apache-2.0
import os
import secrets

import uvicorn

from overlord.config import Settings


def main() -> None:
    settings = Settings()
    if not settings.operator_token:
        os.environ["OVERLORD_OPERATOR_TOKEN"] = secrets.token_urlsafe(32)
        settings = Settings()
    assert settings.operator_token
    print(
        f"Operator panel (private launch credential): http://127.0.0.1:{settings.port}/operator"
        f"#token={settings.operator_token.get_secret_value()}",
        flush=True,
    )
    uvicorn.run(
        "overlord.api:create_app",
        factory=True,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        access_log=False,
    )


if __name__ == "__main__":
    main()
