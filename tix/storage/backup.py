# tix/storage/backup.py
from pathlib import Path
from datetime import datetime
import shutil
import json

BACKUPS_DIRNAME = "backups"

def _backups_dir_for(data_path: Path) -> Path:
    """Return the backups directory path for the given data file path."""
    # place backups in same parent folder as data file: e.g. ~/.tix/backups/
    parent = data_path.expanduser().resolve().parent
    backups_dir = parent / BACKUPS_DIRNAME
    backups_dir.mkdir(parents=True, exist_ok=True)
    return backups_dir

def create_backup(data_path: Path, filename: str = None) -> Path:
    """
    Create a timestamped backup of the given data file.
    - data_path: Path to the tasks data file (e.g. ~/.tix/tasks.json)
    - filename: optional base name provided by user (without extension)
    Returns: Path to the created backup file.
    Raises FileNotFoundError if data file doesn't exist.
    """
    data_path = Path(data_path).expanduser()
    if not data_path.exists():
        raise FileNotFoundError(f"Data file not found: {data_path}")

    backups_dir = _backups_dir_for(data_path)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    if filename:
        # sanitize filename a little
        base = Path(filename).stem
        backup_name = f"{base}_{ts}{data_path.suffix or '.json'}"
    else:
        backup_name = f"backup_{ts}{data_path.suffix or '.json'}"

    backup_path = backups_dir / backup_name
    # copy the file (binary-safe)
    shutil.copy2(str(data_path), str(backup_path))
    return backup_path

def list_backups(data_path: Path):
    """
    List available backup files for the given data file.
    Returns list[Path] sorted descending by modification time.
    """
    backups_dir = _backups_dir_for(Path(data_path))
    files = [p for p in backups_dir.iterdir() if p.is_file()]
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files

def restore_from_backup(backup_file: str, data_path: Path, require_confirm: bool = True):
    """
    Restore the data file from a backup.
    - backup_file: either an absolute path to a backup, or the filename located in backups dir.
    - data_path: the tasks data file path to overwrite.
    - require_confirm: if True, will raise RuntimeError if confirmation wasn't provided (the CLI handles prompt)
    Raises FileNotFoundError if backup cannot be found.
    """
    data_path = Path(data_path).expanduser()
    backups_dir = _backups_dir_for(data_path)

    cand = Path(backup_file)
    if cand.is_absolute() and cand.exists():
        src = cand
    else:
        # treat as basename inside backups dir
        candidate = backups_dir / backup_file
        if candidate.exists():
            src = candidate
        else:
            # try best-effort: if backup_file looks like name without ext, search for matching prefix
            matches = [p for p in backups_dir.iterdir() if p.name.startswith(backup_file)]
            if matches:
                matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                src = matches[0]
            else:
                raise FileNotFoundError(f"Backup not found: {backup_file}")

    # simple restore: copy over data_path (overwrite)
    # ensure destination dir exists
    data_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(src), str(data_path))
    return data_path
