# Examples

`weather_smoke_test.py` runs the joint-weather package on a synthetic point
cloud. It needs only NumPy, with no V2Xverse, CARLA, or GPU.

```bash
python examples/weather_smoke_test.py
```

It checks that the RF2 and RF3 response tables load, and that a seeded run
gives the same output twice. It does not show that the weather model is
realistic.

The packaged tables stop at 13 m, matching the 12 m LiDAR of the final run.
Points beyond that range raise an error.
