#!/usr/bin/env python3
"""Parse browser JavaScript in Node without running browser or connecting network."""
from pathlib import Path
import re
import subprocess
ROOT=Path(__file__).resolve().parents[1]
html=(ROOT/"index.html").read_text(encoding="utf-8")
scripts=re.findall(r"<script(?:\s[^>]*)?>([\s\S]*?)</script>",html,re.I)
assert scripts,"No JavaScript script found"
for script in scripts:
    r=subprocess.run(["node","--check","--input-type=commonjs"],input=script,text=True,capture_output=True)
    if r.returncode:
        raise RuntimeError(r.stderr)
for token in ["relatedFor","paymentFor","gameRegion","gamePlatform","renderCodes","renderGuides"]:
    assert token in html,token
print("PASS: Front-end JS syntax and related feature references")
