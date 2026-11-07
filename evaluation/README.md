# Evaluation

| Script | Purpose | Needs |
|---|---|---|
| `summarize_closed_loop.py` | Rebuilds the tables in `results/closed_loop/` | Python 3.7+ and the raw result folders |
| `stage9b38_collect_closedloop_metrics.py` | Server-side closed-loop collection | `V2XVERSE_ROOT` |
| `stage9b34_collect_openloop_metrics.py` | Offline metric collection | `V2XVERSE_ROOT` |
| `stage9b34f_collect_town05_openloop_metrics.py` | Town05 offline metric collection | `V2XVERSE_ROOT` |
| `stage9b34d_route_bootstrap.py` | Route-level bootstrap for offline metrics | Route metric files |

`summarize_closed_loop.py` was run on the final raw results. For the
`stage9b*` scripts, only hard-coded paths were replaced. They passed syntax
checks but were not run again.
