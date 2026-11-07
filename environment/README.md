# Environment

Versions used for the Stage-9b experiments:

| Component | Version |
|---|---|
| Operating system | Ubuntu 22.04 |
| Python | 3.7.12 |
| PyTorch | 1.13.1+cu117 |
| spconv | spconv-cu113 2.1.21 |
| NumPy | 1.21.6 |
| CARLA | 0.9.10 |

`requirements-freeze.txt` is the `pip freeze` of the server environment. The
three PyTorch packages were installed from local wheels, so their entries were
changed to plain version pins.

## Setup

```bash
conda create -n v2x_client python=3.7.12
conda activate v2x_client
pip install -r environment/requirements-freeze.txt --extra-index-url https://download.pytorch.org/whl/cu117
```

Install CARLA 0.9.10 and V2Xverse separately, following the V2Xverse
instructions. Put the project root first on `PYTHONPATH`, because the `common`
package name can clash with another package.

These install commands were not tested on a clean machine.
