"""Engineering smoke test on synthetic data only (no study data; results are not research results).

Checks CUDA execution, tensor shapes, backward pass, checkpoint writing, and that two runs with the same seed give
bitwise-identical predictions under the deterministic settings.
"""
from __future__ import annotations

import numpy as np
import torch

from src.data import paths
from src.data.io_guard import open_for_write
from src.features.pressure_features import TargetScaler
from src.training.trainer import TCNConfig, device, environment, predict_z, to_tensor, train_tcn


def smoke_test() -> dict:
    rng = np.random.default_rng(0)
    p = rng.integers(0, 4096, size=(3000, 8, 6)).astype(np.int16)
    y = np.stack([20 + p[:, -1, :3].mean(1) / 400, 40 + p[:, -1, 3:].mean(1) / 100], 1)
    sc = TargetScaler.fit(y[:2000], scheme="smoke", fold="0", partition="train", subjects=["synthetic"])
    cfg = TCNConfig(32, 2, 0.1, 1e-3, 1e-4, 256, 3, 5)
    r1 = train_tcn(cfg, p[:2000], y[:2000], sc, 0, pressure_va=p[2000:], y_va=y[2000:], log=lambda m: None)
    r2 = train_tcn(cfg, p[:2000], y[:2000], sc, 0, pressure_va=p[2000:], y_va=y[2000:], log=lambda m: None)
    x = to_tensor(p[2000:], device())
    same = bool(np.array_equal(predict_z(r1.model, x), predict_z(r2.model, x)))
    out = paths.PROJECT_ROOT / "outputs" / "runs" / "p3_smoke" / "model.pt"
    with open_for_write(out, "wb") as fh:
        torch.save(r1.model.state_dict(), fh)
    return {"device": environment()["device"], "epochs": r1.epochs_run, "best_epoch": r1.best_epoch,
            "bitwise_identical_repeat": same, "checkpoint_bytes": out.stat().st_size}
