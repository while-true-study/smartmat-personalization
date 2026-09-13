"""Deterministic TCN training for protocol v1.0 (D-040).

- Inputs: RAW family only in P3 (p / 4095; `src/features/pressure_features.raw`), layout (N, 6, 8).
- Targets: standardised with a training-partition TargetScaler; loss = mean of the two per-target MSEs.
- AdamW, constant learning rate, batch 256, per-epoch shuffling from a seeded CPU generator, no gradient clipping,
  no scheduler (none declared).
- Early stopping (inner runs): the frozen selection criterion on the inner validation subject, patience 5,
  max 50 epochs; best epoch = the first epoch with the lowest criterion (strict improvement only).
- Fixed-epoch training (final outer runs): exactly `epochs` epochs, no validation data at all.
- Determinism: seeded Python/NumPy/PyTorch (CPU+CUDA), torch.use_deterministic_algorithms(True), cuDNN deterministic,
  benchmark off, CUBLAS_WORKSPACE_CONFIG set before CUDA starts.
"""
from __future__ import annotations

import os

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

import copy  # noqa: E402
import itertools  # noqa: E402
import platform  # noqa: E402
import random  # noqa: E402
import time  # noqa: E402
from dataclasses import asdict, dataclass  # noqa: E402
from typing import Callable  # noqa: E402

import numpy as np  # noqa: E402
import torch  # noqa: E402

from src.evaluation.metrics import selection_criterion  # noqa: E402
from src.features.pressure_features import TargetScaler, raw  # noqa: E402
from src.models.tcn import TCN, to_channels_first  # noqa: E402

GRID_KEYS = ("channels", "kernel_size", "dropout", "lr")


@dataclass(frozen=True)
class TCNConfig:
    channels: int
    kernel_size: int
    dropout: float
    lr: float
    weight_decay: float
    batch_size: int
    max_epochs: int
    early_stopping_patience: int

    def as_dict(self) -> dict:
        return asdict(self)


def config_grid(protocol: dict) -> list[TCNConfig]:
    """The 16 declared configurations in declared grid order (itertools.product over the YAML key order)."""
    tcn = protocol["models"]["tcn"]
    space, fixed = tcn["search_space"], tcn["fixed"]
    if tuple(space) != GRID_KEYS:
        raise ValueError(f"search space keys {tuple(space)} != {GRID_KEYS}")
    if fixed["optimizer"] != "adamw":
        raise ValueError("protocol v1.0 fixes AdamW")
    grid = [TCNConfig(c, k, d, lr, fixed["weight_decay"], fixed["batch_size"], fixed["max_epochs"],
                      fixed["early_stopping_patience"])
            for c, k, d, lr in itertools.product(*(space[k] for k in GRID_KEYS))]
    if len(grid) != 16:
        raise ValueError("protocol v1.0 declares exactly 16 configurations")
    return grid


def set_determinism(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def device() -> torch.device:
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def environment() -> dict:
    cuda = torch.cuda.is_available()
    return {"python": platform.python_version(), "torch": torch.__version__, "numpy": np.__version__,
            "cuda_available": cuda, "cuda_version": torch.version.cuda, "cudnn_version": torch.backends.cudnn.version(),
            "device": torch.cuda.get_device_name(0) if cuda else platform.processor(),
            "deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
            "cudnn_deterministic": torch.backends.cudnn.deterministic,
            "cudnn_benchmark": torch.backends.cudnn.benchmark,
            "cublas_workspace_config": os.environ.get("CUBLAS_WORKSPACE_CONFIG"),
            "platform": platform.platform(), "num_workers": 0}


def to_tensor(pressure: np.ndarray, dev: torch.device) -> torch.Tensor:
    """(N, 8, 6) raw pressure -> (N, 6, 8) float32 RAW inputs on the device."""
    return to_channels_first(torch.as_tensor(raw(pressure), dtype=torch.float32)).to(dev)


@torch.no_grad()
def predict_z(model: TCN, x: torch.Tensor, batch: int = 16384) -> np.ndarray:
    model.eval()
    out = [model(x[i:i + batch]).double().cpu().numpy() for i in range(0, x.shape[0], batch)]
    return np.concatenate(out) if out else np.zeros((0, 2))


def is_improvement(value: float, best: float | None) -> bool:
    """Strict improvement only: the first epoch reaching the minimum stays the best epoch."""
    return best is None or value < best


def should_stop(epoch: int, best_epoch: int, patience: int) -> bool:
    """Stop after `patience` consecutive epochs without improvement."""
    return epoch - best_epoch >= patience


def best_epoch_of(criteria: list[float], patience: int, max_epochs: int) -> tuple[int, int]:
    """(best epoch, epochs run) that train_tcn's early stopping yields for a criterion sequence (1-based)."""
    best, best_ep = None, None
    for epoch, c in enumerate(criteria[:max_epochs], start=1):
        if is_improvement(c, best):
            best, best_ep = c, epoch
        if should_stop(epoch, best_ep, patience):
            return best_ep, epoch
    return best_ep, min(len(criteria), max_epochs)


@dataclass
class TrainResult:
    model: TCN
    history: list[dict]
    best_epoch: int | None
    best_score: float | None
    epochs_run: int
    seconds: float


def train_tcn(cfg: TCNConfig, pressure_tr: np.ndarray, y_tr: np.ndarray, scaler: TargetScaler, seed: int, *,
              epochs: int | None = None, pressure_va: np.ndarray | None = None, y_va: np.ndarray | None = None,
              log: Callable[[str], None] = print) -> TrainResult:
    """Either early stopping on (pressure_va, y_va) (inner runs) or exactly `epochs` epochs (final runs)."""
    if (epochs is None) == (pressure_va is None):
        raise ValueError("give either a fixed epoch count or validation data, not both / neither")
    set_determinism(seed)
    dev = device()
    x = to_tensor(pressure_tr, dev)
    y = torch.as_tensor(scaler.transform(y_tr), dtype=torch.float32, device=dev)
    xv = to_tensor(pressure_va, dev) if pressure_va is not None else None
    model = TCN(6, cfg.channels, cfg.kernel_size, cfg.dropout).to(dev)
    opt = torch.optim.AdamW(model.parameters(), lr=cfg.lr, weight_decay=cfg.weight_decay)
    gen = torch.Generator().manual_seed(seed)
    n = x.shape[0]
    max_epochs = epochs if epochs is not None else cfg.max_epochs
    history, best, best_epoch, best_state = [], None, None, None
    t0 = time.time()
    for epoch in range(1, max_epochs + 1):
        model.train()
        perm = torch.randperm(n, generator=gen).to(dev)
        total = torch.zeros((), dtype=torch.float64, device=dev)
        for i in range(0, n, cfg.batch_size):
            idx = perm[i:i + cfg.batch_size]
            loss = torch.nn.functional.mse_loss(model(x[idx]), y[idx])
            opt.zero_grad(set_to_none=True)
            loss.backward()
            opt.step()
            total += loss.detach().double() * idx.numel()
        rec = {"epoch": epoch, "train_loss": float(total) / n}
        if xv is not None:
            pv = scaler.inverse(predict_z(model, xv))
            crit = selection_criterion(y_va, pv, scaler.std)
            rec.update(val_criterion=crit, val_mae_temperature=float(np.mean(np.abs(pv[:, 0] - y_va[:, 0]))),
                       val_mae_humidity=float(np.mean(np.abs(pv[:, 1] - y_va[:, 1]))))
            if is_improvement(crit, best):
                best, best_epoch, best_state = crit, epoch, copy.deepcopy(model.state_dict())
        history.append(rec)
        log(" ".join(f"{k}={v:.6g}" if isinstance(v, float) else f"{k}={v}" for k, v in rec.items()))
        if xv is not None and should_stop(epoch, best_epoch, cfg.early_stopping_patience):
            break
    if best_state is not None:
        model.load_state_dict(best_state)
    return TrainResult(model, history, best_epoch, best, len(history), time.time() - t0)
