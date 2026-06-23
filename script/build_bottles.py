import tarfile
import tempfile
import shutil
import sys
from pathlib import Path

def build_bottle(archive_path: str, version: str, bottle_name: str):
    """Convert flat archive to Homebrew bottle structure."""
    print(f"Building {bottle_name} from {archive_path}...")

    with tempfile.TemporaryDirectory() as tmpdir:
        with tarfile.open(archive_path, 'r:gz') as tar:
            tar.extractall(tmpdir)

        wrench_dir = Path(tmpdir) / "wrench" / version
        wrench_dir.mkdir(parents=True, exist_ok=True)

        for item in Path(tmpdir).iterdir():
            if item.name != "wrench":
                shutil.move(str(item), str(wrench_dir / item.name))

        wrench_parent = Path(tmpdir) / "wrench"
        if wrench_parent.exists() and wrench_parent.is_dir():
            for item in wrench_parent.iterdir():
                if item.name != version:
                    shutil.move(str(item), str(wrench_dir / item.name))
            for item in wrench_parent.iterdir():
                if item.is_dir() and not any(item.iterdir()):
                    item.rmdir()

        bottle_path = Path(archive_path).parent / bottle_name
        with tarfile.open(bottle_path, 'w:gz') as tar:
            tar.add(Path(tmpdir) / "wrench", arcname="wrench")

    print(f"Created {bottle_name}")
    return bottle_path

def main():
    version = sys.argv[1]
    release_dir = Path("release")

    mapping = {
        "wrench-macOS-ARM64.tar.gz": f"wrench-{version}.arm64_ventura.bottle.tar.gz",
        "wrench-Linux-ARM64.tar.gz": f"wrench-{version}.arm64_linux.bottle.tar.gz",
        "wrench-Linux-X64.tar.gz": f"wrench-{version}.x86_64_linux.bottle.tar.gz",
    }

    for src, dst in mapping.items():
        src_path = release_dir / src
        if src_path.exists():
            build_bottle(str(src_path), version, dst)
        else:
            print(f"⚠️ {src} not found, skipping")

if __name__ == "__main__":
    main()