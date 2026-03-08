from __future__ import annotations

import importlib
import os
import sys


REQUIRED = ("vectorbt", "jesse")


def main() -> None:
    strict = os.getenv("REQUIRE_BACKTEST_RUNTIMES", "").strip().lower() == "true"
    missing: list[str] = []

    for name in REQUIRED:
        try:
            module = importlib.import_module(name)
            version = getattr(module, "__version__", "unknown")
            print(f"{name}: {version}")
        except Exception as exc:
            print(f"{name}: unavailable ({exc})")
            missing.append(name)

    if missing and strict:
        raise SystemExit(f"Missing required backtest runtimes in strict mode: {', '.join(missing)}")


if __name__ == "__main__":
    main()
