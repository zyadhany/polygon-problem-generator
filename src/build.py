from __future__ import annotations

import argparse
import base64
from pathlib import Path
from typing import Any

from .config import ConfigError, load_problem_config, load_tests_file
from .polygon_api import polygon_api_call
from .polygon_methods import *


class BuildError(RuntimeError):
    pass


def _stage(number: int, title: str, fn) -> None:
    label = f"STAGE {number}: {title}"
    print(label)
    try:
        fn()
    except Exception as exc:
        raise BuildError(f"{label} FAILED: {exc}") from exc
    print(f"{label} DONE")


def _log(msg: str, verbose: bool) -> None:
    if verbose:
        print(msg)


def _read_text(path: str) -> str:
    # utf-8-sig removes BOM (\ufeff) if present
    return Path(path).read_text(encoding="utf-8-sig")


def _read_base64(path: str) -> str:
    return base64.b64encode(Path(path).read_bytes()).decode("ascii")


def _resolve_path(base_dir: Path, value: str) -> str:
    p = Path(value)
    if not p.is_absolute():
        p = (base_dir / p).resolve()
    return str(p)


def _call(method_key: str, params: dict[str, Any], dry_run: bool, verbose: bool) -> Any:
    method_name = get_method(method_key)
    _log(f"[polygon] {method_name} params={params}", verbose)
    if dry_run:
        return None
    try:
        return polygon_api_call(method_name, params)
    except Exception as exc:
        raise BuildError(f"Polygon call failed for {method_name}: {exc}") from exc


def _is_not_found(err: Exception) -> bool:
    text = str(err).lower()
    return "not found" in text or "does not exist" in text


def _load_samples(samples_path: str) -> list[dict[str, str]]:
    samples = load_tests_file(samples_path)
    for idx, sample in enumerate(samples):
        if not isinstance(sample, dict):
            raise ConfigError(f"Expected object for samples[{idx}]")
        if "in" not in sample or "out" not in sample:
            raise ConfigError(f"Missing in/out for samples[{idx}]")
    return samples


def _load_manuals(manuals_path: str) -> list[dict[str, str]]:
    manuals = load_tests_file(manuals_path)
    for idx, item in enumerate(manuals):
        if not isinstance(item, dict):
            raise ConfigError(f"Expected object for manuals[{idx}]")
        if "in" not in item:
            raise ConfigError(f"Missing in for manuals[{idx}]")
    return manuals


def build(config_path: str, dry_run: bool, verbose: bool) -> None:
    cfg = load_problem_config(config_path)
    data = cfg.raw

    problem = data.get("problem", {})
    statement = data.get("statement", {})
    files = data.get("files", {})
    tests = data.get("tests", {})

    print()
    polygon_name = problem.get("polygon_name")
    if not polygon_name:
        raise BuildError("problem.polygon_name is required")

    state: dict[str, Any] = {"problem_id": None}

    def stage1() -> None:
        polygon_id = None
        exists = False
        try:
            polygon_id = PL_check_problem_exists(polygon_name)
            exists = polygon_id is not None
        except BuildError as exc:
            if _is_not_found(exc):
                exists = False
            else:
                raise

        if exists:
            state["problem_id"] = polygon_id
            _log(f"Using existing problem_id={polygon_id}", verbose)
            return

        _log(f"Problem not found; creating new problem named '{polygon_name}'", verbose)
        polygon_id = PL_create_problem(polygon_name)
        if dry_run:
            state["problem_id"] = polygon_id
            return

    def stage2() -> None:
        pid = state["problem_id"]
        _call(
            "update_info",
            {
                "problemId": pid,
                "timeLimit": problem["timelimit_ms"],
                "memoryLimit": problem["memory_mb"],
            },
            dry_run,
            verbose,
        )
        tags = problem.get("tags")
        if tags:
            _call(
                "set_tags",
                {
                    "problemId": pid,
                    "tags": tags,
                },
                dry_run,
                verbose,
            )

    def stage3() -> None:
        pid = state["problem_id"]
        language = statement.get("language", "english")
        if language != "english":
            raise BuildError("statement.language must be 'english' for this flow")

        _call(
            "save_statement",
            {
                "problemId": pid,
                "lang": language,
                "name": problem["name"],
                "legend": _read_text(statement["legend_md"]),
                "input": _read_text(statement["input_md"]),
                "output": _read_text(statement["output_md"]),
                # "notes": _read_text(statement["notes_md"]),
                # "tutorial": _read_text(statement["tutorial_md"]),
            },
            dry_run,
            verbose,
        )


    def stage4() -> None:
        pid = state["problem_id"]
        checker = files.get("checker")
        _call(
            "checker_set",
            {
                "problemId": pid,
                "checker": checker,
            },
            dry_run,
            verbose,
        )

    def stage5() -> None:
        pid = state["problem_id"]
        validator_path = files.get("validator_path")
        validator_name = Path(validator_path).name
        _call(
            "files_save",
            {
                "problemId": pid,
                "type": "validator",
                "name": validator_name,
                "content": _read_text(validator_path),
            },
            dry_run,
            verbose,
        )
        _call(
            "validator_set",
            {
                "problemId": pid,
                "validator": validator_name,
            },
            dry_run,
            verbose,
        )

    def stage6() -> None:
        pid = state["problem_id"]
        solutions = files.get("solutions", [])
        main = next((s for s in solutions if s.get("tag") == "main"), None)
        if not main:
            raise BuildError("No solution with tag == 'main' found")

        sol_path = main["path"]
        sol_name = Path(sol_path).name
        result = _call(
            "solution_add",
            {
                "problemId": pid,
                "name": sol_name,
                "language": main["language"],
                "content": _read_text(sol_path),
                "tag": main.get("tag"),
            },
            dry_run,
            verbose,
        )

        sol_id = None
        if not dry_run and isinstance(result, dict):
            sol_id = result.get("id") or result.get("solutionId")
        _call(
            "solution_set_main",
            {
                "problemId": pid,
                "solutionId": sol_id or sol_name,
            },
            dry_run,
            verbose,
        )

    def stage7() -> None:
        pid = state["problem_id"]
        samples = _load_samples(tests.get("samples_path"))
        manuals = _load_manuals(tests.get("manuals_path"))

        for idx, sample in enumerate(samples, start=1):
            sample_in = _resolve_path(cfg.base_dir, sample["in"])
            sample_out = _resolve_path(cfg.base_dir, sample["out"])
            _call(
                "tests_add",
                {
                    "problemId": pid,
                    "testName": f"sample_{idx}",
                    "input": _read_text(sample_in),
                    "output": _read_text(sample_out),
                    "type": "sample",
                },
                dry_run,
                verbose,
            )

        for idx, manual in enumerate(manuals, start=1):
            manual_in = _resolve_path(cfg.base_dir, manual["in"])
            _call(
                "tests_add_manual",
                {
                    "problemId": pid,
                    "testName": f"manual_{idx}",
                    "input": _read_text(manual_in),
                },
                dry_run,
                verbose,
            )

        generators = tests.get("generators", [])
        for gen_idx, gen in enumerate(generators, start=1):
            gen_path = gen["path"]
            gen_name = Path(gen_path).name
            _call(
                "files_save",
                {
                    "problemId": pid,
                    "type": "generator",
                    "name": gen_name,
                    "content": _read_text(gen_path),
                },
                dry_run,
                verbose,
            )

            repeat = gen["repeat"]
            for seed in range(1, repeat + 1):
                test_name = f"gen_{gen_idx}_{seed}"
                cmd = f"./gen {seed}"
                _call(
                    "tests_generate",
                    {
                        "problemId": pid,
                        "generator": gen_name,
                        "commandLine": cmd,
                        "testName": test_name,
                        "seed": seed,
                    },
                    dry_run,
                    verbose,
                )


    _stage(1, "Problem init (by polygon_id)", stage1)
    _stage(2, "Basic settings", stage2)
    _stage(3, "English statement", stage3)
    exit(0)
    _stage(4, "Checker", stage4)
    _stage(5, "Validator", stage5)
    _stage(6, "Main solution", stage6)
    _stage(7, "Tests", stage7)

    print("Build completed.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Polygon problem from YAML config")
    parser.add_argument("--config", default="problem.yaml")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    try:
        build(args.config, args.dry_run, args.verbose)
    except ConfigError as exc:
        raise SystemExit(f"Config error:\n{exc}")
    except BuildError as exc:
        raise SystemExit(f"Build error: {exc}")


if __name__ == "__main__":
    main()
