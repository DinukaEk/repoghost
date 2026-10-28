"""Create a harmless sample Git repo in demo_repository/."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ghostcore.sample import create_demo_repo

if __name__ == "__main__":
    dest = Path(__file__).resolve().parents[1] / "demo_repository"
    try:
        print(f"Demo created at: {create_demo_repo(dest)}")
    except FileExistsError as exc:
        print(f"Demo already exists: {exc}")
