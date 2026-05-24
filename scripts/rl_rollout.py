from pathlib import Path
import runpy

target = Path(__file__).resolve().parent / "rl" / "rl_rollout.py"
runpy.run_path(str(target), run_name="__main__")
