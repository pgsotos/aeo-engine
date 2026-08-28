#!/usr/bin/env python
"""Write the OpenAPI schema to a file, for tooling that cannot reach a server.

    uv run python scripts/export_openapi.py [output.json]

Defaults to `openapi.json` next to this script's parent (backend/).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from aeo_engine.main import app


def main() -> None:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("openapi.json")
    target.write_text(json.dumps(app.openapi(), indent=2) + "\n")
    print(f"wrote {target} ({len(app.openapi()['paths'])} paths)")


if __name__ == "__main__":
    main()
