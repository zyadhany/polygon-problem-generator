from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class ConfigError(ValueError):
    pass


@dataclass
class LoadedConfig:
    raw: dict
    path: Path
    base_dir: Path


def _require(mapping: dict, key: str, ctx: str, errors: list[str]) -> Any:
    if key not in mapping:
        errors.append(f"Missing '{ctx}.{key}'")
        return None
    return mapping[key]


def _require_str(value: Any, ctx: str, errors: list[str]) -> str | None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"Expected non-empty string for '{ctx}'")
        return None
    return value


def _require_int(value: Any, ctx: str, errors: list[str]) -> int | None:
    if not isinstance(value, int):
        errors.append(f"Expected integer for '{ctx}'")
        return None
    return value


def _require_list(value: Any, ctx: str, errors: list[str]) -> list | None:
    if not isinstance(value, list):
        errors.append(f"Expected list for '{ctx}'")
        return None
    return value


def _resolve_path(base: Path, value: str | None) -> str | None:
    if not value:
        return None
    p = Path(value)
    if not p.is_absolute():
        p = (base / p).resolve()
    return str(p)


def load_problem_config(path: str) -> LoadedConfig:
    cfg_path = Path(path).resolve()
    with cfg_path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    errors: list[str] = []

    problem = raw.get("problem")
    if not isinstance(problem, dict):
        errors.append("Missing or invalid 'problem' section")
        problem = {}

    _require_str(_require(problem, "polygon_name", "problem", errors), "problem.polygon_name", errors)
    _require_str(_require(problem, "name", "problem", errors), "problem.name", errors)
    _require_int(_require(problem, "timelimit_ms", "problem", errors), "problem.timelimit_ms", errors)
    _require_int(_require(problem, "memory_mb", "problem", errors), "problem.memory_mb", errors)

    tags = problem.get("tags")
    if tags is not None:
        tag_list = _require_list(tags, "problem.tags", errors)
        if tag_list is not None:
            for idx, tag in enumerate(tag_list):
                _require_str(tag, f"problem.tags[{idx}]", errors)

    statement = raw.get("statement")
    if not isinstance(statement, dict):
        errors.append("Missing or invalid 'statement' section")
        statement = {}

    language = statement.get("language", "english")
    if not isinstance(language, str):
        errors.append("Expected string for 'statement.language'")

    for field in ["legend_md", "input_md", "output_md", "notes_md"]:
        _require_str(_require(statement, field, "statement", errors), f"statement.{field}", errors)

    files = raw.get("files")
    if not isinstance(files, dict):
        errors.append("Missing or invalid 'files' section")
        files = {}

    _require_str(_require(files, "checker", "files", errors), "files.checker", errors)
    _require_str(_require(files, "validator_path", "files", errors), "files.validator_path", errors)

    solutions = files.get("solutions", [])
    if not isinstance(solutions, list):
        errors.append("Expected list for 'files.solutions'")
        solutions = []

    for idx, sol in enumerate(solutions):
        if not isinstance(sol, dict):
            errors.append(f"Expected object for 'files.solutions[{idx}]'")
            continue
        _require_str(sol.get("path"), f"files.solutions[{idx}].path", errors)
        _require_str(sol.get("language"), f"files.solutions[{idx}].language", errors)
        _require_str(sol.get("tag"), f"files.solutions[{idx}].tag", errors)

    tests = raw.get("tests")
    if not isinstance(tests, dict):
        errors.append("Missing or invalid 'tests' section")
        tests = {}

    _require_str(_require(tests, "samples_path", "tests", errors), "tests.samples_path", errors)

    generators = tests.get("generators", [])
    if not isinstance(generators, list):
        errors.append("Expected list for 'tests.generators'")
        generators = []

    for idx, gen in enumerate(generators):
        if not isinstance(gen, dict):
            errors.append(f"Expected object for 'tests.generators[{idx}]'")
            continue
        _require_str(gen.get("path"), f"tests.generators[{idx}].path", errors)
        _require_str(gen.get("language"), f"tests.generators[{idx}].language", errors)
    if errors:
        raise ConfigError("\n".join(errors))

    base_dir = cfg_path.parent

    statement["legend_md"] = _resolve_path(base_dir, statement.get("legend_md"))
    statement["input_md"] = _resolve_path(base_dir, statement.get("input_md"))
    statement["output_md"] = _resolve_path(base_dir, statement.get("output_md"))
    statement["notes_md"] = _resolve_path(base_dir, statement.get("notes_md"))
    statement["tutorial_md"] = _resolve_path(base_dir, statement.get("tutorial_md"))
    statement["images_dir"] = _resolve_path(base_dir, statement.get("images_dir"))

    files["validator_path"] = _resolve_path(base_dir, files.get("validator_path"))
    for sol in solutions:
        sol["path"] = _resolve_path(base_dir, sol.get("path"))

    tests["samples_path"] = _resolve_path(base_dir, tests.get("samples_path"))
    for gen in generators:
        gen["path"] = _resolve_path(base_dir, gen.get("path"))

    return LoadedConfig(raw=raw, path=cfg_path, base_dir=base_dir)


def load_tests_file(path: str) -> list[dict[str, Any]]:
    if not path:
        return []
    p = Path(path)
    if not p.exists():
        raise ConfigError(f"Tests file not found: {path}")
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ConfigError(f"Expected list in tests file: {path}")
    return data
