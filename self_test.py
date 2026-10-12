# -*- coding: utf-8 -*-
"""self_test for metric-definition-dict — inherits scaffold v2 four defenses:
  D1 SystemExit/BaseException capture in run_cli
  D2 Unicode-safe patterns (CJK/emoji fixtures)
  D3 fixtures written with newline="" (Windows CRLF safe)
  D4 last line `SUMMARY: PASS n/n`
"""
import contextlib, io, json, os, sys, tempfile, unittest

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", newline="\n")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import importlib
mod = importlib.import_module("metric_definition_dict")
main = mod.main


def run_cli(argv):
    """D1: catch SystemExit and Exception; return (code, stdout, stderr)."""
    buf_out, buf_err = io.StringIO(), io.StringIO()
    code = 0
    try:
        with contextlib.redirect_stdout(buf_out), contextlib.redirect_stderr(buf_err):
            main(argv)
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
    except Exception as e:
        code = 1
        buf_err.write(repr(e))
    return code, buf_out.getvalue(), buf_err.getvalue()


def _write(text, suffix=".json"):
    """D3: newline="" prevents \r\n double-write on Windows."""
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    return path


def _spec(*metrics):
    return json.dumps({"metrics": list(metrics)})


def _good(**kw):
    m = {"id": "rev", "name": "Revenue", "kind": "sum", "window": "30d",
         "numerator": "amount"}
    m.update(kw)
    return m


CASES = []


def case(fn):
    CASES.append(fn)
    return fn


# ---------------- [A] functional ----------------

@case
def a01_validate_good_spec_exit0():
    p = _write(_spec(_good(), _good(id="cnt", name="Count", kind="count", numerator=None)))
    code, out, _ = run_cli(["validate", p])
    assert code == 0 and "OK" in out, (code, out)


@case
def a02_validate_json_output_parseable():
    p = _write(_spec(_good()))
    code, out, _ = run_cli(["validate", p, "--json"])
    assert code == 0
    assert json.loads(out)["findings"] == []


@case
def a03_validate_exit1_on_error():
    p = _write(_spec(_good(window="banana")))
    code, out, _ = run_cli(["validate", p])
    assert code == 1 and "R6" in out


@case
def a04_validate_exit0_warning_only():
    p = _write(_spec(_good(kind="count", denominator="x")))
    code, out, _ = run_cli(["validate", p])
    assert code == 0 and "R9" in out


@case
def a05_r1_empty_metrics_list():
    p = _write('{"metrics": []}')
    code, out, _ = run_cli(["validate", p])
    assert code == 1 and "R1" in out


@case
def a06_r2_missing_id():
    p = _write(_spec({"name": "X", "kind": "sum", "window": "30d"}))
    code, out, _ = run_cli(["validate", p])
    assert code == 1 and "R2" in out


@case
def a07_r3_duplicate_id():
    p = _write(_spec(_good(), _good()))
    code, out, _ = run_cli(["validate", p])
    assert code == 1 and "R3" in out


@case
def a08_r4_empty_name():
    p = _write(_spec(_good(name="   ")))
    code, out, _ = run_cli(["validate", p])
    assert code == 1 and "R4" in out


@case
def a09_r5_unknown_kind():
    p = _write(_spec(_good(kind="median")))
    code, out, _ = run_cli(["validate", p])
    assert code == 1 and "R5" in out


@case
def a10_r6_bad_window():
    p = _write(_spec(_good(window="30")))
    code, out, _ = run_cli(["validate", p])
    assert code == 1 and "R6" in out


@case
def a11_r7_empty_numerator_string():
    p = _write(_spec(_good(numerator="")))
    code, out, _ = run_cli(["validate", p])
    assert code == 1 and "R7" in out


@case
def a12_r8_ratio_missing_denominator():
    p = _write(_spec(_good(kind="ratio", denominator=None)))
    code, out, _ = run_cli(["validate", p])
    assert code == 1 and "R8" in out


@case
def a13_check_c1_redefined_id():
    p = _write(_spec(_good(), _good(window="7d")))
    code, out, _ = run_cli(["check", p])
    assert code == 1 and "C1" in out


@case
def a14_check_c2_identical_duplicate_warning():
    p = _write(_spec(_good(), _good()))
    code, out, _ = run_cli(["check", p])
    assert code == 0 and "C2" in out


@case
def a15_check_c3_name_collision():
    p = _write(_spec(_good(), _good(id="rev2", name="revenue")))
    code, out, _ = run_cli(["check", p])
    assert code == 0 and "C3" in out


@case
def a16_check_json_output():
    p = _write(_spec(_good(), _good(id="b", name="Revenue")))
    code, out, _ = run_cli(["check", p, "--json"])
    assert code == 0 and json.loads(out)["findings"]


@case
def a17_direct_validate_dict_function():
    assert mod.validate_dict({"metrics": [_good()]}) == []


@case
def a18_direct_find_conflicts_clean():
    assert mod.find_conflicts({"metrics": [_good(), _good(id="b", name="Other")]}) == []


@case
def a19_bench_small_runs():
    code, out, _ = run_cli(["bench", "--metrics", "50"])
    assert code == 0 and "validate=" in out and "metrics=50" in out


@case
def a20_bench_default_runs():
    code, out, _ = run_cli(["bench"])
    assert code == 0 and "rec/s" in out


@case
def a21_help_exit0():
    code, out, _ = run_cli(["--help"])
    assert code == 0 and "metric-definition-dict" in out


@case
def a22_no_args_exit2():
    code, _, _ = run_cli([])
    assert code == 2


@case
def a23_unknown_subcommand_exit2():
    code, _, _ = run_cli(["frobnicate"])
    assert code == 2


# ---------------- [B] exception paths ----------------

@case
def b01_missing_file():
    code, _, err = run_cli(["validate", "Z:/no/such/file.json"])
    assert code == 1 and "cannot read" in err


@case
def b02_invalid_json():
    p = _write("{not json")
    code, _, err = run_cli(["validate", p])
    assert code == 1 and "invalid JSON" in err


@case
def b03_spec_is_list_not_object():
    p = _write("[]")
    code, out, _ = run_cli(["validate", p])
    assert code == 1 and "R0" in out


@case
def b04_spec_is_string():
    p = _write('"hello"')
    code, out, _ = run_cli(["validate", p])
    assert code == 1 and "R0" in out


@case
def b05_metrics_is_dict():
    p = _write('{"metrics": {"id": "x"}}')
    code, out, _ = run_cli(["validate", p])
    assert code == 1 and "R1" in out


@case
def b06_metrics_missing_key():
    p = _write("{}")
    code, out, _ = run_cli(["validate", p])
    assert code == 1 and "R1" in out


@case
def b07_metric_not_object():
    p = _write('{"metrics": [42]}')
    code, out, _ = run_cli(["validate", p])
    assert code == 1 and "R2" in out


@case
def b08_id_is_number():
    p = _write(_spec({"id": 7, "name": "X", "kind": "sum", "window": "30d"}))
    code, out, _ = run_cli(["validate", p])
    assert code == 1 and "R2" in out


@case
def b09_id_starts_with_digit():
    p = _write(_spec(_good(id="1abc")))
    code, out, _ = run_cli(["validate", p])
    assert code == 1 and "R2" in out


@case
def b10_name_is_number():
    p = _write(_spec(_good(name=99)))
    code, out, _ = run_cli(["validate", p])
    assert code == 1 and "R4" in out


@case
def b11_window_is_number():
    p = _write(_spec(_good(window=30)))
    code, out, _ = run_cli(["validate", p])
    assert code == 1 and "R6" in out


@case
def b12_window_reversed_format():
    p = _write(_spec(_good(window="d30")))
    code, out, _ = run_cli(["validate", p])
    assert code == 1 and "R6" in out


@case
def b13_kind_is_none():
    p = _write(_spec(_good(kind=None)))
    code, out, _ = run_cli(["validate", p])
    assert code == 1 and "R5" in out


@case
def b14_numerator_is_list():
    p = _write(_spec(_good(numerator=["a"])))
    code, out, _ = run_cli(["validate", p])
    assert code == 1 and "R7" in out


@case
def b15_bench_metrics_zero():
    code, _, _ = run_cli(["bench", "--metrics", "0"])
    assert code == 2


@case
def b16_bench_metrics_negative():
    code, _, _ = run_cli(["bench", "--metrics", "-3"])
    assert code == 2


@case
def b17_bench_metrics_not_int():
    code, _, _ = run_cli(["bench", "--metrics", "abc"])
    assert code == 2


@case
def b18_check_on_missing_file():
    code, _, err = run_cli(["check", "Z:/nope.json"])
    assert code == 1 and "cannot read" in err


@case
def b19_check_truncated_json():
    p = _write('{"metrics": [')
    code, _, err = run_cli(["check", p])
    assert code == 1 and "invalid JSON" in err


@case
def b20_directory_as_input():
    code, _, err = run_cli(["validate", os.path.dirname(os.path.abspath(__file__))])
    assert code == 1 and "cannot read" in err


# ---------------- [C] extreme / edge ----------------

@case
def c01_empty_file():
    p = _write("")
    code, _, err = run_cli(["validate", p])
    assert code == 1 and "invalid JSON" in err


@case
def c02_whitespace_only_file():
    p = _write("   \n\t  ")
    code, _, err = run_cli(["validate", p])
    assert code == 1


@case
def c03_utf8_bom_file():
    fd, p = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    with open(p, "wb") as fh:
        fh.write(b"\xef\xbb\xbf" + _spec(_good()).encode("utf-8"))
    code, out, _ = run_cli(["validate", p])
    assert code == 0, (code, out)


@case
def c04_huge_name_100k():
    p = _write(_spec(_good(name="M" * 100000)))
    code, _, _ = run_cli(["validate", p])
    assert code == 0


@case
def c05_unicode_cjk_name():
    p = _write(_spec(_good(name="营收（月度）")))
    code, out, _ = run_cli(["validate", p])
    assert code == 0


@case
def c06_unicode_emoji_name():
    p = _write(_spec(_good(name="Revenue \U0001f4b0 ok")))
    code, _, _ = run_cli(["validate", p])
    assert code == 0


@case
def c07_unicode_cjk_id_rejected():
    p = _write(_spec(_good(id="营收")))
    code, out, _ = run_cli(["validate", p])
    assert code == 1 and "R2" in out


@case
def c08_max_length_id_64_ok():
    p = _write(_spec(_good(id="a" * 64)))
    code, _, _ = run_cli(["validate", p])
    assert code == 0


@case
def c09_id_65_chars_rejected():
    p = _write(_spec(_good(id="a" * 65)))
    code, out, _ = run_cli(["validate", p])
    assert code == 1 and "R2" in out


@case
def c10_window_999999mo_ok():
    p = _write(_spec(_good(window="999999mo")))
    code, _, _ = run_cli(["validate", p])
    assert code == 0


@case
def c11_window_zero_day_accepted_by_grammar():
    p = _write(_spec(_good(window="0d")))
    code, _, _ = run_cli(["validate", p])
    assert code == 0


@case
def c12_all_time_window_ok():
    p = _write(_spec(_good(window="all_time")))
    code, _, _ = run_cli(["validate", p])
    assert code == 0


@case
def c13_extra_top_level_keys_ignored():
    p = _write('{"metrics": [%s], "version": 9, "notes": "x"}' % json.dumps(_good()))
    code, _, _ = run_cli(["validate", p])
    assert code == 0


@case
def c14_extra_metric_fields_ignored():
    p = _write(_spec(_good(owner="team-a", labels={"a": 1})))
    code, _, _ = run_cli(["validate", p])
    assert code == 0


@case
def c15_name_case_insensitive_collision():
    p = _write(_spec(_good(), _good(id="b2", name="REVENUE")))
    code, out, _ = run_cli(["check", p])
    assert code == 0 and "C3" in out


@case
def c16_100_metrics_bulk():
    p = _write(_spec(*[_good(id="m%03d" % i, name="M%d" % i) for i in range(100)]))
    code, _, _ = run_cli(["validate", p])
    assert code == 0


@case
def c17_100_duplicate_names_no_crash():
    ms = [_good(id="m%03d" % i, name="Same") for i in range(100)]
    p = _write(_spec(*ms))
    code, out, _ = run_cli(["check", p])
    assert code == 0 and out.count("C3") >= 1


@case
def c18_crlf_line_endings_file():
    fd, p = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    with open(p, "w", encoding="utf-8", newline="") as fh:  # D3
        fh.write('{\r\n "metrics": [%s]\r\n}\r\n' % json.dumps(_good()))
    code, _, _ = run_cli(["validate", p])
    assert code == 0


@case
def c19_deeply_nested_extra_field():
    deep = {"a": [{"b": {"c": [1, 2, {"d": "e"}]}}] * 50}
    p = _write(_spec(_good(extra=deep)))
    code, _, _ = run_cli(["validate", p])
    assert code == 0


@case
def c20_ratio_same_num_den_valid():
    p = _write(_spec(_good(kind="ratio", numerator="x", denominator="x")))
    code, _, _ = run_cli(["validate", p])
    assert code == 0


class T(unittest.TestCase):
    def test_meta_case_count(self):
        self.assertGreaterEqual(len(CASES), 60)


for _fn in CASES:
    setattr(T, "test_" + _fn.__name__, lambda self, f=_fn: f())

if __name__ == "__main__":
    r = unittest.TextTestRunner(verbosity=0).run(
        unittest.defaultTestLoader.loadTestsFromModule(sys.modules["__main__"]))
    total, fails = r.testsRun, len(r.failures) + len(r.errors)
    print("SUMMARY: PASS %d/%d" % (total - fails, total))
    sys.exit(0 if fails == 0 else 1)
