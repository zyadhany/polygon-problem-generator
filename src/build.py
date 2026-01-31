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
        if "in" not in sample:
            raise ConfigError(f"Missing in for samples[{idx}]")
        if not isinstance(sample["in"], str):
            raise ConfigError(f"Expected string for samples[{idx}].in")
        if "out" in sample and not isinstance(sample["out"], str):
            raise ConfigError(f"Expected string for samples[{idx}].out")
        if "example" in  sample and sample["example"] not in ("true", "false"):
            raise ConfigError(f"Expected 'true' or 'false' for samples[{idx}].example")
    return samples


def _load_manuals(manuals_path: str) -> list[dict[str, str]]:
    manuals = load_tests_file(manuals_path)
    for idx, item in enumerate(manuals):
        if not isinstance(item, dict):
            raise ConfigError(f"Expected object for manuals[{idx}]")
        if "in" not in item:
            raise ConfigError(f"Missing in for manuals[{idx}]")
    return manuals


def add_file_source(problem_id: int, file_path: str, dry_run: bool = False, verbose: bool = False) -> None:
    file_name = Path(file_path).name
    _call(
        "save_file",
        {
            "problemId": problem_id,
            "type": "source",
            "name": file_name,
            "file": _read_text(file_path),
        },
        dry_run,
        verbose,
    )

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
        checker = "std::" + files.get("checker")

        ret = _call(
            "set_checker",
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

        add_file_source(pid, validator_path, dry_run, verbose)
        _call(
            "set_validator",
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
        main = next((s for s in solutions if s.get("tag") == "MA"), None)
        if not main:
            raise BuildError("No solution with tag == 'MA' found")

        sol_path = main["path"]
        sol_name = Path(sol_path).name
        result = _call(
            "save_solution",
            {
                "problemId": pid,
                "name": sol_name,
                "file": _read_text(sol_path),
                "tag": main.get("tag"),
            },
            dry_run,
            verbose,
        )

    def stage7() -> None:
        pid = state["problem_id"]
        samples = _load_samples(tests.get("samples_path"))

        script_cmd = _call(
            "script",
            {"problemId": pid,"testset": "tests",},
            dry_run,
            verbose,
        )
        if script_cmd not in (None, ""):
            _call(
                "save_script",
                {
                    "problemId": pid,
                    "testset": "tests",
                    "source": " ", 
                },
                dry_run,
                verbose,
            )

        for idx, sample in enumerate(samples, start=1):
            sample_in = sample.get("in")
            sample_out = sample.get("out", "")
            is_sample = sample.get("example", "false")
               
            _call(
                "save_test",
                {
                    "problemId": pid,
                    "testset": "tests",
                    "testIndex": idx,
                    "testInput": sample_in,
                    "testUseInStatements": is_sample,
                    "testOutputForStatements": sample_out, 
                },
                dry_run,
                verbose,
            )
        
        if script_cmd not in (None, ""):
            _call(
                "save_script",
                {
                    "problemId": pid,
                    "testset": "tests",
                    "source": script_cmd, 
                },
                dry_run,
                verbose,
            )

    def stage8() -> None:
        pid = state["problem_id"]
        generators = tests.get("generators", [])

        script_cmd = ""
        cnt = 1

        for gen_idx, gen in enumerate(generators, start=1):
            gen_path = gen["path"]
            gen_name = Path(gen_path).stem
            repeat = gen.get("repeat", 1)
            cmd = gen.get("cmd", "")

            if cmd not in ("", None):
                script_cmd += f"\n{cmd}"
            else:
                """
                    <#list 1..10 as i >
                        igen --m 10 ${i} > $ 
                    </#list>
                """
                script_cmd += f"\n<#list {cnt}..{cnt + repeat - 1} as i >\n"
                script_cmd += f"   {gen_name} ${{i}} > $\n"
                script_cmd += "</#list>\n"
                cnt += repeat
            
            add_file_source(pid, gen_path, dry_run, verbose)
        _call(
            "save_script",
            {
                "problemId": pid,
                "testset": "tests",
                "source": script_cmd, 
            },
            dry_run,
            verbose,
        )

    def stage9() -> None:
        pid = state["problem_id"]
        _call(
            "commit_changes",
            {
                "problemId": pid,
                "minorChanges": "true", 
            },
            dry_run,
            verbose,
        )

        _call(
            "build_package",
            {
                "problemId": pid,
                "full": "false",
                "verify": "true", 
            },
            dry_run,
            verbose,
        )
        pass


    _stage(1, "Problem init (by polygon_id)", stage1)
    # _stage(2, "Basic settings", stage2)
    # _stage(3, "English statement", stage3)
    # _stage(4, "Checker", stage4)
    # _stage(5, "Validator", stage5)
    # _stage(6, "Main solution", stage6)
    # _stage(7, "Manual_Tests", stage7)
    # _stage(8, "Generated_Tests", stage8)
    _stage(9, "commit and Package", stage9)
    exit(0)

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
