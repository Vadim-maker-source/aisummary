"""Compatibility entry point for the canonical project dataset generator."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.generate_project_dataset import main  # noqa: E402


if __name__ == "__main__":
    main()
