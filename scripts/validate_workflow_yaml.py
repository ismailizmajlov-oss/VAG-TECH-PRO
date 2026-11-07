import pathlib
import sys

import yaml

def validate(path: pathlib.Path) -> None:
    text = path.read_text(encoding="utf-8")
    if "\\${{" in text:
        raise SystemExit("Workflow contains escaped GitHub expressions: " + str(path))
    try:
        doc = yaml.load(text, Loader=yaml.BaseLoader)
    except yaml.YAMLError as exc:
        print(str(path) + ": " + str(exc))
        raise SystemExit(1) from exc
    if not isinstance(doc, dict):
        raise SystemExit("Workflow root must be a mapping: " + str(path))
    if "jobs" not in doc or not isinstance(doc["jobs"], dict) or not doc["jobs"]:
        raise SystemExit("Workflow must contain at least one job: " + str(path))
    for job_id, job in doc["jobs"].items():
        if not isinstance(job, dict) or not isinstance(job.get("steps"), list):
            raise SystemExit("Job " + repr(job_id) + " has no steps list in " + str(path))
        ids = [step.get("id") for step in job["steps"] if isinstance(step, dict) and step.get("id")]
        if len(ids) != len(set(ids)):
            raise SystemExit("Job " + repr(job_id) + " has duplicate step ids in " + str(path))
    print("YAML syntax and basic Actions structure valid: " + str(path))

def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("Usage: validate_workflow_yaml.py WORKFLOW.yml [WORKFLOW.yml ...]")
    for argument in sys.argv[1:]:
        validate(pathlib.Path(argument))

if __name__ == "__main__":
    main()
