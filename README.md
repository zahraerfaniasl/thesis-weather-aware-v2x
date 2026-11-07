# Weather-Aware V2X Cooperative Perception

Thesis work on how much cooperative perception protects vulnerable road
users (VRUs), and whether a roadside-unit (RSU) radar helps when rain and
fog degrade LiDAR. The experiments build on V2Xverse, OpenCOOD, and
CARLA 0.9.10.

## Project status

This repository records the **Stage-9b experiments**, which are finished.
Their main closed-loop result is not a valid test of radar fusion, and the
next stage will revise both the radar and the weather model.

| Question | Current state |
|---|---|
| Does radar help offline detection? | Early evidence for pedestrians, from small samples |
| Does radar help closed-loop driving? | **Not tested yet.** Radar input to the model was zero in the final run |
| Does the weather model degrade LiDAR realistically? | **No.** It removed no LiDAR points in the final closed-loop run |

## Method

Two cooperative perception models are compared. Both use the
`center_point_codriving` model with CoDriving attention fusion.

- **Baseline:** cooperative LiDAR only.
- **Density:** cooperative LiDAR plus RSU radar density. The radar BEV is
  warped into the ego frame and fused additively.

Weather conditions are `OFF`, `RF2` (rain 50 mm/h, fog 0.06 1/m), and `RF3`
(rain 50 mm/h, fog 0.20 1/m).

## Results

Full tables and sources are in [`results/`](results/README.md).

### Offline detection

Seven-route Town05 subset, 3327 frames, one training seed, `net_epoch3.pth`:

| Metric | OFF: Baseline | OFF: Density | RF3: Baseline | RF3: Density |
|---|---:|---:|---:|---:|
| mAP@0.3 | 0.280 | 0.278 | 0.192 | 0.211 |
| mAP@0.5 | 0.166 | 0.199 | 0.147 | 0.160 |
| Pedestrian AP@0.5 | 0.024 | 0.113 | 0.036 | 0.058 |
| Vehicle AP@0.5 | 0.372 | 0.377 | 0.352 | 0.337 |

The gain is mainly for pedestrians. It is not a general improvement:
Vehicle AP@0.5 under RF3 is lower for Density, and mAP@0.3 under OFF is
about equal.

### Closed-loop driving

Town05, 73 counted jobs per cell, `net_epoch_bestval_at1.pth`:

| Weather | Driving score: Baseline | Driving score: Density | Density minus Baseline (95% CI) | Collisions: Baseline | Collisions: Density |
|---|---:|---:|---:|---:|---:|
| OFF | 64.95 | 57.55 | -7.40 [-14.66, 0.16] | 77 | 81 |
| RF2 | 62.98 | 54.53 | -8.45 [-14.40, -2.40] | 81 | 104 |
| RF3 | 63.71 | 56.48 | -7.23 [-14.50, 0.43] | 82 | 88 |

Baseline scored higher in this run, but **this is not a measure of the
effect of radar**, as explained below.

## Known limitations

1. **Radar did not reach the model in closed loop.** With
   `stage9b_online_radar: false`, the radar input was all zeros. The gap
   above compares two differently trained checkpoints. This comes from the
   code and configuration, and still needs a trace-based check on the server.
2. **Weather did not degrade the LiDAR in closed loop.** Traces show `lost=0`
   and `fog=0`, with a 12 m LiDAR range and `pmin = 2.25e-05`.
3. **Training was short and used clear weather only.** The best validation
   checkpoint came from epoch 1.
4. **The radar covers little of the scene.** Its mounting covers about 13% of
   the ego BEV (estimated after the run).
5. **Different stages used different models.** Screening used the
   `stage9b_clean_*_pilot` models, the Town05 test used `confirm3`
   `net_epoch3.pth`, and closed loop used `confirm3`
   `net_epoch_bestval_at1.pth`.
6. **Samples are small.** Results use one seed, six validation routes, and
   seven offline test routes. In closed loop, 12 of 85 jobs per cell have no
   ego-level result record.

## Planned work

- Replace the radar setup and make it reach the model in closed loop.
- Replace the weather model with a more realistic one.
- Retrain both models with an equal budget across weather conditions.
- Rerun the closed-loop matrix with radar input tracing and more seeds.

Analysis behind these items is in [`docs/`](docs/README.md).

## Repository layout

| Path | Contents |
|---|---|
| `configs/` | Portable experiment, weather, radar, and closed-loop settings |
| `src/radar/` | RSU radar processing modules |
| `src/weather_augmentation/` | Joint rain-fog LiDAR augmentation and response tables |
| `src/fusion/` | Fusion settings (source stays upstream) |
| `src/integration/` | How the modules connect to V2Xverse |
| `scripts/` | Training and experiment drivers |
| `evaluation/` | Metric collection and statistics |
| `results/` | Small result tables |
| `docs/` | Methodology and stage analyses |
| `environment/` | Software versions and setup |
| `examples/` | Quick checks |

## Reproducing the work

This repository is **not a standalone runnable project yet**. It holds the
thesis components, not a full V2Xverse tree. Radar integration needs changes
to upstream files, which will be published only if redistribution is
permitted (see `src/integration/README.md`). Datasets and checkpoints are
not included.

To check the weather package on its own, see
[`examples/`](examples/README.md).

## Licensing

Code written for this thesis and third-party code have different terms. See
[`LICENSE`](LICENSE) and [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

## Citation

Citation details are in [`CITATION.cff`](CITATION.cff). Please also cite the
V2Xverse paper:

```bibtex
@article{liu2024codriving,
  title={Towards Collaborative Autonomous Driving: Simulation Platform and End-to-End System},
  author={Liu, Genjia and Hu, Yue and Xu, Chenxin and Mao, Weibo and Ge, Junhao and Huang, Zhengxiang and Lu, Yifan and Xu, Yinda and Xia, Junkai and Wang, Yafei and others},
  journal={arXiv preprint arXiv:2404.09496},
  year={2024}
}
```
