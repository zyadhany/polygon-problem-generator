from .polygon_api import polygon_api_call

"""Central list of Polygon API method names.

Edit these strings to match the exact Polygon API you use.
Only method names live here to avoid scattering string literals.
"""

# Each entry is (method_name, confirmed).
# If confirmed is False, get_method will raise with a TODO message.
# Each entry is (method_name, confirmed).
# These names are from Polygon API docs (see "Methods" list).
from src.polygon_api import polygon_api_call


METHODS: dict[str, tuple[str, bool]] = {
    # Problems
    "list_problems": ("problems.list", True),
    "create_problem": ("problem.create", True),
    "problem_info": ("problem.info", True),
    "update_info": ("problem.updateInfo", True),
    "commit_changes": ("problem.commitChanges", True),
    "update_working_copy": ("problem.updateWorkingCopy", True),
    "discard_working_copy": ("problem.discardWorkingCopy", True),

    # Tags
    "save_tags": ("problem.saveTags", True),

    # Statements + resources
    "statements": ("problem.statements", True),
    "save_statement": ("problem.saveStatement", True),
    "statement_resources": ("problem.statementResources", True),
    "save_statement_resource": ("problem.saveStatementResource", True),

    # Files (generic)
    "files": ("problem.files", True),
    "save_file": ("problem.saveFile", True),
    "view_file": ("problem.viewFile", True),

    # Checker / Validator
    "checker": ("problem.checker", True),
    "set_checker": ("problem.setChecker", True),
    "validator": ("problem.validator", True),
    "set_validator": ("problem.setValidator", True),

    # Solutions
    "solutions": ("problem.solutions", True),
    "save_solution": ("problem.saveSolution", True),  # use tag="MA" for main

    # Scripts (generators/interactor/etc.)
    "script": ("problem.script", True),
    "save_script": ("problem.saveScript", True),

    # Tests
    "tests": ("problem.tests", True),
    "save_test": ("problem.saveTest", True),
    "test_input": ("problem.testInput", True),
    "test_answer": ("problem.testAnswer", True),

    # Optional validator/checker tests (only if you need them)
    "validator_tests": ("problem.validatorTests", True),
    "save_validator_test": ("problem.saveValidatorTest", True),
    "checker_tests": ("problem.checkerTests", True),
    "save_checker_test": ("problem.saveCheckerTest", True),
}



def get_method(key: str) -> str:
    entry = METHODS.get(key)
    if not entry:
        raise KeyError(f"Missing Polygon method name for: {key}")
    method, confirmed = entry
    if not confirmed:
        raise RuntimeError(
            f"Polygon method name for '{key}' is unconfirmed. "
            f"Assumed '{method}'. Please update src/polygon_methods.py."
        )
    return method


"""
    check if a problem with the given name exists
    return id if exists, else None
"""
def PL_check_problem_exists(name: str) -> int | None:
    resp = polygon_api_call("problems.list", {"name": name})
    if resp is None or len(resp) == 0:
        return None
    return resp[0]['id']

"""
    create a new problem with the given name
    return the new problem id
"""
def PL_create_problem(name: str) -> int:
    if PL_check_problem_exists(name):
        raise RuntimeError(f"Problem with name '{name}' already exists")
    resp = polygon_api_call("problem.create", {"name": name})
    problem_id = resp.get("id")
    if problem_id is None:
        raise RuntimeError("Failed to create problem")
    return problem_id