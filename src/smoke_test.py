from .polygon_api import polygon_api_call
from .polygon_methods import *

def set_limits(problem_id: str, time_ms: int, memory_mb: int) -> None:
    # 1) update limits
    r = polygon_api_call("problem.updateInfo", {
        "problemId": problem_id,
        "timeLimit": time_ms,
        "memoryLimit": memory_mb,
    })
    if r.get("status") != "OK":
        raise RuntimeError(f"updateInfo failed: {r.get('comment')}")

    # 2) commit
    r = polygon_api_call("problem.commitChanges", {
        "problemId": problem_id,
        "message": f"Set TL={time_ms}ms, ML={memory_mb}MB",
        "minorChanges": "true",  # optional
    })
    if r.get("status") != "OK":
        raise RuntimeError(f"commitChanges failed: {r.get('comment')}")

def set_english_statement_name(problem_id: str) -> None:
    """
    Creates/updates the English statement and sets ONLY its title/name.
    Does not touch legend/input/output/notes/tutorial.
    """
    resp = polygon_api_call("problem.saveStatement", {
        "problemId": problem_id,
        "lang": "english",
        "encoding": "UTF-8",
        "name": "Two Sum",
    })
    print(resp)

    # if resp.get("status") != "OK":
    #     raise RuntimeError(f"problem.saveStatement failed: {resp}")

def main() -> None:
    tests = polygon_api_call("problems.list", {
        "name": "test-api",
    })
    print(tests)
    # set_limits("506229", 2000, 256)
    # set_english_statement_name("506229")
    # method_name = get_method("update_info")
    # params =  {
    #     "problemId": 506229,
    #     "timeLimit": 2000,
    # },
    # # print(method_name)
    # # return
    # polygon_api_call("problem.updateInfo", params)
    # result = PL_check_problem_exists("taest-api")
    # print(result)
    # # print(f"Problems: {len(result)}")


if __name__ == "__main__":
    main()
