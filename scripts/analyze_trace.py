from pathlib import Path
import runpy

target = Path(__file__).resolve().parent / "rl" / "analyze_trace.py"
runpy.run_path(str(target), run_name="__main__")
