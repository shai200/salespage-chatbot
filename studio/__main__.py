from __future__ import annotations

import uvicorn

from studio import config


def main() -> None:
    uvicorn.run(
        "studio.app:app",
        host=config.STUDIO_HOST,
        port=config.STUDIO_PORT,
        reload=False,
    )


if __name__ == "__main__":
    main()
