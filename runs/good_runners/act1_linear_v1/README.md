# Act 1 Linear-Q Good Runners

This folder contains the current stable class-specific Linear-Q runners.

Use this manifest for benchmarks:

```powershell
python scripts\benchmark_linear_runners.py --manifest runs\good_runners\act1_linear_v1\manifest.json --runs-per-character 100 --seed 130001 --max-steps 800 --out-dir runs\rl_balance_checks --stem act1_linear_v1_check
```

Each character subfolder contains `best_linear_q_agent.json`.
