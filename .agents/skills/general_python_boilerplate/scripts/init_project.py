import os
import sys
import argparse
from pathlib import Path

def create_structure(target_dir: Path):
    """Creates the standard Synapsis folder structure.
    
    Args:
        target_dir: Root directory of the new project.
    """
    folders = [
        "data_model",
        "database/helper",
        "database/instance",
        "database/migration",
        "database/seeder",
        "inference",
        "interfaces",
        "models",
        "pipeline",
        "test",
        "utils",
        ".agent/rules",
        ".agent/workflows",
    ]
    
    for folder in folders:
        path = target_dir / folder
        path.mkdir(parents=True, exist_ok=True)
        (path / ".gitkeep").touch()
        print(f"Created folder: {folder}")

def create_base_files(target_dir: Path):
    """Creates base configuration and entry files.
    
    Args:
        target_dir: Root directory of the new project.
    """
    files = {
        "main.py": 'def main():\n    print("Hello Synapsis!")\n\nif __name__ == "__main__":\n    main()',
        ".env.example": "PORT=5000\nDATABASE_URL=postgres://user:pass@localhost:5432/db",
        ".gitignore": ".env\n__pycache__/\n.venv/\n*.db\n.mypy_cache/\n.ruff_cache/\n.pytest_cache/\n",
        "README.md": "# New Project\nGenerated from Synapsis General Boilerplate.",
    }
    
    for filename, content in files.items():
        file_path = target_dir / filename
        if not file_path.exists():
            file_path.write_text(content)
            print(f"Created file: {filename}")

def main():
    parser = argparse.ArgumentParser(description="Initialize a Synapsis General Python Project.")
    parser.add_argument("path", nargs="?", default=".", help="Target path for initialization.")
    parser.add_argument("--test", action="store_true", help="Dry run for testing.")
    
    args = parser.parse_args()
    target_path = Path(args.path).absolute()
    
    if args.test:
        print(f"[TEST] Would initialize project at {target_path}")
        return

    print(f"Initializing project at {target_path}...")
    create_structure(target_path)
    create_base_files(target_path)
    print("Initialization complete.")

if __name__ == "__main__":
    main()

<!-- managed -->
