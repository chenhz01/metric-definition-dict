#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""metric-definition-dict — a declarative dictionary for metric definitions
(definition / denominator / time window) plus conflict detection between
metric entries. Pure standard library, single file, offline.
"""
import argparse, json, re, sys, time

ID_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
WINDOW_RE = re.compile(r"^(?:all_time|\d+(?:h|d|w|mo|q|y))$")
KINDS = ("count", "sum", "ratio", "gauge", "distinct")

DEF_KEYS = ("kind", "window", "numerator", "denominator")


def _err(findings, rule, severity, msg, metric=None):
    f = {"rule": rule, "severity": severity, "message": msg}
    if metric is not None:
        f["metric"] = metric
    findings.append(f)


def validate_dict(spec):
    """Structural validation. Returns a list of finding dicts."""
    findings = []
    if not isinstance(spec, dict):
        _err(findings, "R0", "error", "spec must be a JSON object")
        return findings
    metrics = spec.get("metrics")
    if not isinstance(metrics, list) or not metrics:
        _err(findings, "R1", "error", "metrics must be a non-empty list")
        return findings
    seen = set()
    for i, m in enumerate(metrics):
        ref = m.get("id") if isinstance(m, dict) else "#%d" % (i + 1)
        if not isinstance(m, dict):
            _err(findings, "R2", "error", "metric entry is not an object", ref)
            continue
        mid = m.get("id")
        if not isinstance(mid, str) or not ID_RE.match(mid):
            _err(findings, "R2", "error", "id missing or not [A-Za-z_][A-Za-z0-9_]{0,63}", ref)
            continue
        if mid in seen:
            _err(findings, "R3", "error", "duplicate metric id", mid)
            continue
        seen.add(mid)
        name = m.get("name")
        if not isinstance(name, str) or not name.strip():
            _err(findings, "R4", "error", "name must be a non-empty string", mid)
        kind = m.get("kind")
        if kind not in KINDS:
            _err(findings, "R5", "error", "kind must be one of %s" % "|".join(KINDS), mid)
        window = m.get("window")
        if not isinstance(window, str) or not WINDOW_RE.match(window):
            _err(findings, "R6", "error", "window must be all_time or <n><h|d|w|mo|q|y>", mid)
        num, den = m.get("numerator"), m.get("denominator")
        for label, v in (("numerator", num), ("denominator", den)):
            if v is not None and (not isinstance(v, str) or not v.strip()):
                _err(findings, "R7", "error", "%s must be a non-empty string when present" % label, mid)
        if kind == "ratio":
            if not isinstance(num, str) or not num.strip():
                _err(findings, "R8", "error", "ratio metric requires a numerator", mid)
            if not isinstance(den, str) or not den.strip():
                _err(findings, "R8", "error", "ratio metric requires a denominator", mid)
        if kind == "count" and den is not None:
            _err(findings, "R9", "warning", "count metric declares a denominator (ignored)", mid)
    return findings


def find_conflicts(spec):
    """Semantic conflict detection between metric entries."""
    findings = []
    metrics = spec.get("metrics") if isinstance(spec, dict) else None
    if not isinstance(metrics, list):
        return findings
    by_id, by_name = {}, {}
    for m in metrics:
        if not isinstance(m, dict):
            continue
        mid, name = m.get("id"), m.get("name")
        if isinstance(mid, str):
            if mid in by_id:
                prev = by_id[mid]
                if any(prev.get(k) != m.get(k) for k in DEF_KEYS):
                    _err(findings, "C1", "error", "id redefined with a different definition", mid)
                else:
                    _err(findings, "C2", "warning", "id declared twice with an identical definition", mid)
            else:
                by_id[mid] = m
        if isinstance(name, str) and name.strip():
            key = name.strip().lower()
            if key in by_name and by_name[key] != mid:
                _err(findings, "C3", "warning", "same name claimed by two different ids", name)
            else:
                by_name.setdefault(key, mid)
    return findings


def _has_error(findings):
    return any(f["severity"] == "error" for f in findings)


def _load(path):
    with open(path, "r", encoding="utf-8-sig") as fh:
        return json.load(fh)


def _print(findings, as_json):
    if as_json:
        print(json.dumps({"findings": findings}, ensure_ascii=False, indent=2))
    else:
        if not findings:
            print("OK: no findings")
        for f in findings:
            loc = " [%s]" % f["metric"] if f.get("metric") else ""
            print("%-7s %-4s%s %s" % (f["severity"], f["rule"], loc, f["message"]))


def _positive_int(text):
    try:
        v = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError("not an integer: %r" % text)
    if v < 1:
        raise argparse.ArgumentTypeError("must be >= 1")
    return v


def bench(n):
    spec = {"metrics": [
        {"id": "m%05d" % i, "name": "Metric %05d" % i, "kind": "sum",
         "window": "30d", "numerator": "col_a", "denominator": "col_b"}
        for i in range(n)]}
    t0 = time.perf_counter()
    f1 = validate_dict(spec)
    t1 = time.perf_counter()
    f2 = find_conflicts(spec)
    t2 = time.perf_counter()
    return len(f1), len(f2), t1 - t0, t2 - t1


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="metric-definition-dict",
        description="Validate metric definition dictionaries and detect definition conflicts.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    pv = sub.add_parser("validate", help="structural validation of a dictionary file")
    pv.add_argument("spec")
    pv.add_argument("--json", action="store_true")

    pc = sub.add_parser("check", help="conflict detection across metric entries")
    pc.add_argument("spec")
    pc.add_argument("--json", action="store_true")

    pb = sub.add_parser("bench", help="run validation on synthetic metrics and time it")
    pb.add_argument("--metrics", type=_positive_int, default=10000)

    args = ap.parse_args(argv)
    if args.cmd == "bench":
        e1, e2, dt_v, dt_c = bench(args.metrics)
        print("metrics=%d validate=%.4fs (%.0f rec/s) conflicts=%.4fs findings=%d/%d"
              % (args.metrics, dt_v, args.metrics / dt_v if dt_v else 0, dt_c, e1, e2))
        sys.exit(0)

    try:
        spec = _load(args.spec)
    except OSError as exc:
        print("error: cannot read %s: %s" % (args.spec, exc), file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as exc:
        print("error: invalid JSON in %s: %s" % (args.spec, exc), file=sys.stderr)
        sys.exit(1)

    findings = validate_dict(spec) if args.cmd == "validate" else find_conflicts(spec)
    _print(findings, args.json)
    sys.exit(1 if _has_error(findings) else 0)


if __name__ == "__main__":
    sys.exit(main())
