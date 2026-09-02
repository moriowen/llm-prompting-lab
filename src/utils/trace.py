"""One JSONL file per experiment cell, with a config header and per-line flush."""

import json
import re
from pathlib import Path

RUNS = Path("runs")


def cell_path(model_alias: str, task: str, arm: str, temp: float,
              ladder: bool = False) -> Path:
    """runs/<model>[/ladder]/<task>.<arm>.t<temp>.jsonl -- the path encodes the whole cell."""
    slug = re.sub(r"[^A-Za-z0-9._-]", "_", model_alias)
    # The ladder reuses qids Q1.. for entirely different queries, so its trials must
    # never share a file with the main run: --resume keys on (qid, seed) and would
    # otherwise skip ladder items as already done.
    directory = RUNS / slug / "ladder" if ladder else RUNS / slug
    return directory / f"{task}.{arm}.t{temp}.jsonl"


def done_keys(path: Path) -> set[tuple[str, int]]:
    """(qid, seed) pairs already recorded, so --resume can skip them."""
    if not path.exists():
        return set()
    keys = set()
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue  # a run killed mid-write leaves a partial last line
            if rec.get("type") == "trial":
                keys.add((rec["qid"], rec["seed"]))
    return keys


class Trace:
    """Appends trials to one cell file, writing the header only when creating it."""

    def __init__(self, model_alias: str, task: str, arm: str, temp: float,
                 resume: bool = True, **header):
        self.path = cell_path(model_alias, task, arm, temp, header.get("ladder", False))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.done = done_keys(self.path) if resume else set()
        fresh = not (resume and self.path.exists())
        self.file = self.path.open("a" if not fresh else "w")
        self.n = len(self.done)
        if fresh:
            self._write({"type": "run", "model": model_alias, "task": task,
                         "arm": arm, "temperature": temp, **header})

    def _write(self, record: dict) -> None:
        self.file.write(json.dumps(record, default=str) + "\n")
        # A run killed by thermal throttling must still leave an analysable prefix.
        self.file.flush()

    def trial(self, **fields) -> None:
        """Record one call: prompt, raw response, grade, timings, stop reason."""
        self.n += 1
        self._write({"type": "trial", "n": self.n, **fields})

    def close(self) -> None:
        self.file.close()


def load(path) -> list[dict]:
    """Read one cell file."""
    records = []
    with Path(path).open() as f:
        for line in f:
            if line.strip():
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return records


def load_all(root=RUNS) -> tuple[list[dict], list[dict]]:
    """(headers, trials) across every committed run file."""
    headers, trials = [], []
    for path in sorted(Path(root).rglob("*.jsonl")):
        records = load(path)
        if not records or records[0].get("type") != "run":
            continue
        head = records[0]
        headers.append({**head, "path": str(path)})
        for rec in records[1:]:
            if rec.get("type") == "trial":
                trials.append({**rec, "model": head["model"], "task": head["task"],
                               "arm": head["arm"], "temperature": head["temperature"],
                               "ladder": bool(head.get("ladder"))})
    return headers, trials
