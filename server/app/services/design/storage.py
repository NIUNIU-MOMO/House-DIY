import json
from pathlib import Path

from app.schemas.design_spec import DesignSpec

DESIGNSPEC_FILENAME = "designspec.json"


def get_design_spec_path(project_id: int) -> Path:
    from app.services.floorplan.storage import get_project_dir

    return get_project_dir(project_id) / DESIGNSPEC_FILENAME


def save_design_spec(project_id: int, spec: DesignSpec) -> Path:
    path = get_design_spec_path(project_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(spec.model_dump_json(indent=2), encoding="utf-8")
    return path


def load_design_spec(project_id: int) -> DesignSpec | None:
    path = get_design_spec_path(project_id)
    if not path.is_file():
        return None
    return DesignSpec.model_validate(json.loads(path.read_text(encoding="utf-8")))
