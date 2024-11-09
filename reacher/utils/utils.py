from datetime import datetime
from pathlib import Path


def get_latest_run(base_path, resume=False):
    """
    Find the most recent directory in a nested structure like Oct-29/13-01-34/
    Returns the full path to the most recent time directory
    """
    all_dirs = []
    base_path = Path(base_path)

    # find all dates
    for date_dir in base_path.iterdir():
        if not date_dir.is_dir():
            continue
        # find all times
        for time_dir in date_dir.iterdir():
            if not time_dir.is_dir():
                continue
            try:
                dir_datetime = datetime.strptime(
                    f"{date_dir.name}/{time_dir.name}", "%b-%d/%H-%M-%S"
                )
                all_dirs.append((time_dir, dir_datetime))
            except ValueError:
                continue

    # sort
    sorted_directories = sorted(all_dirs, key=lambda x: x[1], reverse=True)
    target_dir = sorted_directories[1][0] if resume else sorted_directories[0][0]
    
    # get latest model
    model_files = list(target_dir.glob("model_*.pt"))
    latest_model_file = max(model_files, key=lambda x: x.stat().st_mtime)
    return latest_model_file
