# Stage-9b experiment matrices

This directory records the experimental design used for offline method
selection and final closed-loop evaluation.

## Offline screening

The offline screening consisted of sixteen evaluations:

- four methods;
- four weather conditions;
- one evaluation for each method and weather pair.

The evaluated methods were:

1. Baseline without radar fusion;
2. Density;
3. Density + Doppler;
4. Density + Doppler + Gate.

Each method was evaluated under `OFF`, `RF1`, `RF2`, and `RF3`.

Baseline was the reference method. The other three methods were radar
fusion candidates.

Density was reported as the only converged radar candidate. It was
selected for final closed-loop evaluation alongside the baseline.

The complete sixteen-cell design is recorded in
`offline_screening_matrix.yaml`.

## Final closed-loop evaluation

The final closed-loop matrix contained:

- Baseline and Density;
- weather conditions `OFF`, `RF2`, and `RF3`;
- configuration families `8_10`, `5_10`, and `5_50`;
- training seed `2029`.

The route-part mapping was:

| Part | Configuration family |
|---|---|
| `1s` | `8_10` |
| `2s` | `5_10` |
| `3s` | `5_10` |
| `4s` | `8_10` |
| `5s` | `5_50` |

There are eighteen unique packaged closed-loop configurations:

`2 methods x 3 weather conditions x 3 configuration families = 18`.

RF1 was used during offline screening but was not included in the final
closed-loop weather matrix.

## Configuration availability

The repository contains operational offline configurations for the final
Baseline and Density methods under `OFF`, `RF2`, and `RF3`.

Separate operational YAML files for every cell of the earlier screening
matrix are not reproduced because their exact audited source variants
have not been packaged. No missing parameter values were guessed.

This directory records the verified experimental design and selection
decision without inventing numerical results.
