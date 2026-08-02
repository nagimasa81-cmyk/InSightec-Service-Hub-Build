from pathlib import Path

root = Path(__file__).resolve().parents[1]
main = (root / "LogMergeTool_NoExcel_Main.py").read_text(encoding="utf-8")
start = main.index("@dataclass\nclass LogRecord:")
end = main.index("\n@dataclass\nclass RunOptions", start)
segment = main[start:end]

for token in ["_KEY_ALIASES", "def get(", "def __getitem__(", "def items("]:
    assert token in segment, token
assert "self.__dict__.copy()" not in segment

print("Commit0032A zero-copy compatibility: PASS")
