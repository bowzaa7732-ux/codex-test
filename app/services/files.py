from pathlib import Path, PurePosixPath


class UnsafePathError(ValueError):
    pass


class WorkspaceService:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def safe_path(self, project_id: int, relative: str) -> Path:
        candidate_path = PurePosixPath(relative.replace("\\", "/"))
        if candidate_path.is_absolute() or not relative or ".." in candidate_path.parts:
            raise UnsafePathError("Path must be relative and cannot contain '..'")
        project_root = (self.root / str(project_id)).resolve()
        candidate = (project_root / Path(*candidate_path.parts)).resolve()
        if not candidate.is_relative_to(project_root):
            raise UnsafePathError("Path escapes the project workspace")
        return candidate

    def write(self, project_id: int, relative: str, content: str) -> None:
        target = self.safe_path(project_id, relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

