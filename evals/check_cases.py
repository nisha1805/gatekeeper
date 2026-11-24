"""Checks cases.json against the real rules: the stated tier must be what the classifier gives
for the expected answers. Run from the repo root: python evals/check_cases.py"""
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "app" / "compliance"))
from classifier import SystemDescription, Role, AnnexIIIArea, classify
from questions import BY_FIELD

bad = 0
for c in json.load(open(pathlib.Path(__file__).with_name("cases.json")))["cases"]:
    kw = {}
    for f, v in c["expect"].items():
        assert f in BY_FIELD, (c["id"], f)
        kw[f] = Role(v) if f == "role" else frozenset(AnnexIIIArea(x) for x in v) if f == "annex3_areas" else v
    for f in c["allowed_extra"]:
        assert f in BY_FIELD, (c["id"], f)
    got = classify(SystemDescription(**kw)).tier.value
    flag = "ok " if got == c["tier"] else "BAD"
    bad += got != c["tier"]
    print(flag, c["id"], "states", c["tier"], "rules give", got)
sys.exit(1 if bad else 0)
