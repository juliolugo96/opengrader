"""Start an isolated real OpenGrader API for browser end-to-end tests."""

from pathlib import Path
from tempfile import TemporaryDirectory

import uvicorn

from opengrader.api import create_app
from opengrader.api_models import ApiSettings


def main() -> None:
    with TemporaryDirectory(prefix="opengrader-platform-e2e-") as temporary:
        root = Path(temporary)
        application = create_app(
            ApiSettings(
                database_path=root / "opengrader.db",
                output_root=root / "reports",
                pdf_storage_root=root / "pdfs",
                assignment_storage_root=root / "assignments",
                api_keys=("platform-e2e-key",),
                poll_interval=0.01,
            )
        )
        uvicorn.run(
            application,
            host="127.0.0.1",
            port=8100,
            log_level="warning",
        )


if __name__ == "__main__":
    main()
