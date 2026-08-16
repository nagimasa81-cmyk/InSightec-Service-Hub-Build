from pathlib import Path
import re, sys

text = Path("app.js").read_text(encoding="utf-8")
required = [
    "isGreen",
    "detectGraph",
    "plotInsets",
    "colorSamples",
    "foregroundTraceForHue",
    "genericTrace",
    "analyze",
    "runPostCapturePipeline",
    "foregroundChannelFromHue",
    "channelDecision",
    "axisLabelHypotheses",
    "fitAxisLabelSequence",
    "yAxisCalibration",
]
missing = []
for name in required:
    if not re.search(rf"\bfunction\s+{re.escape(name)}\s*\(", text):
        missing.append(name)

if missing:
    print("Missing runtime helper(s):", ", ".join(missing))
    sys.exit(1)

# isGreen is especially critical because app.js references it throughout the
# ROI/grid/foreground pipeline and JS syntax checking alone cannot catch a
# missing global function.
refs = len(re.findall(r"\bisGreen\s*\(", text))
if refs < 2:
    print("Unexpected isGreen reference count:", refs)
    sys.exit(1)

print("Runtime helper regression check PASS")
