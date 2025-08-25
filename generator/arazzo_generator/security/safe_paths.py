"""Safe path handling for the Arazzo generator."""

import os
import pathlib

# The project root is always considered a safe directory for local file access.
PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
SAFE_ROOTS = [PROJECT_ROOT]

def _is_filesystem_root(path: pathlib.Path) -> bool:
    """Check if the given path is a filesystem root."""
    # A path is a root if it's absolute and has only one part (e.g., '/' or 'C:\').
    return path.is_absolute() and len(path.parts) == 1

def add_external_root():
    """Add an external safe directory from an environment variable if it's valid."""
    external_dir = os.environ.get("OPENAPI_SPECS_DIR")
    if not external_dir:
        return

    try:
        external_path = pathlib.Path(external_dir).resolve(strict=True)
        if _is_filesystem_root(external_path):
            raise ValueError("Filesystem root directories are not allowed as external spec roots.")
        SAFE_ROOTS.append(external_path)
    except (FileNotFoundError, ValueError) as e:
        # Silently ignore invalid or non-existent directories.
        print(f"Warning: Invalid OPENAPI_SPECS_DIR: {e}")

def is_within_safe_roots(path: str | pathlib.Path) -> bool:
    """Check if a given path is within one of the configured safe roots."""
    try:
        # If path is string, normalize it before Path construction
        if isinstance(path, str):
            # Use normpath to collapse '..' and '.', but leave absolute/relative as is
            normed = os.path.normpath(path)
            path_obj = pathlib.Path(normed)
        elif isinstance(path, pathlib.Path):
            path_obj = path
        else:
            # If neither, reject
            return False
        # Explicitly reject absolute paths that are directly the filesystem root
        if _is_filesystem_root(path_obj):
            return False
        resolved_path = path_obj.resolve(strict=True)
        for root in SAFE_ROOTS:
            root_resolved = root.resolve(strict=True)
            # Compare with explicit boundary check (Path.relative_to throws if not inside)
            try:
                resolved_path.relative_to(root_resolved)
                return True
            except ValueError:
                continue
        return False
    except (ValueError, FileNotFoundError):
        return False
