import pathlib
import sys
import yaml

path = pathlib.Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
if "\\${{" in text:
    raise SystemExit("Workflow contains escaped GitHub expressions (\\${{).")
try:
    doc = yaml.load(text, Loader=yaml.BaseLoader)
except yaml.YAMLError as exc:
    print(exc)
    raise SystemExit(1)
if not isinstance(doc, dict):
    raise SystemExit("Workflow root must be a mapping.")
if "jobs" not in doc or not isinstance(doc["jobs"], dict) or not doc["jobs"]:
    raise SystemExit("Workflow must contain at least one job.")
for job_id, job in doc["jobs"].items():
    if not isinstance(job, dict) or not isinstance(job.get("steps"), list):
        raise SystemExit(f"Job {job_id!r} has no steps list.")
    ids = [step.get("id") for step in job["steps"] if isinstance(step, dict) and step.get("id")]
    if len(ids) != len(set(ids)):
        raise SystemExit(f"Job {job_id!r} has duplicate step ids.")
print(f"YAML syntax and basic Actions structure valid: {path}")
