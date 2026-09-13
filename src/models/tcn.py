"""Causal residual TCN of protocol v1.0 (D-040; docs/EXPERIMENT_PROTOCOL.md §9).

Exactly the declared components, nothing added (no weight normalisation, no batch/layer norm, no attention):
- 3 residual blocks with dilations 1, 2, 4;
- each block: causal Conv1d -> ReLU -> Dropout -> causal Conv1d -> ReLU -> Dropout, plus the residual path
  (identity, or a 1x1 Conv1d when the channel count changes); block output = ReLU(main + residual);
- causal convolution = left zero-padding of (kernel_size - 1) * dilation, so step t sees only steps <= t;
- head: Linear(channels -> 2) on the last time step (temperature, humidity; standardised units).
Input layout: (N, C=6, T=8). `to_channels_first` converts the protocol's (N, T, C) windows explicitly.
"""
from __future__ import annotations

import torch
from torch import nn

DILATIONS = (1, 2, 4)


class CausalConv1d(nn.Module):
    def __init__(self, c_in: int, c_out: int, kernel_size: int, dilation: int):
        super().__init__()
        self.pad = (kernel_size - 1) * dilation
        self.conv = nn.Conv1d(c_in, c_out, kernel_size, dilation=dilation)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.conv(nn.functional.pad(x, (self.pad, 0)))


class TemporalBlock(nn.Module):
    def __init__(self, c_in: int, c_out: int, kernel_size: int, dilation: int, dropout: float):
        super().__init__()
        self.main = nn.Sequential(
            CausalConv1d(c_in, c_out, kernel_size, dilation), nn.ReLU(), nn.Dropout(dropout),
            CausalConv1d(c_out, c_out, kernel_size, dilation), nn.ReLU(), nn.Dropout(dropout))
        self.residual = nn.Conv1d(c_in, c_out, 1) if c_in != c_out else nn.Identity()
        self.out = nn.ReLU()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.out(self.main(x) + self.residual(x))


class TCN(nn.Module):
    def __init__(self, in_channels: int = 6, channels: int = 32, kernel_size: int = 2, dropout: float = 0.1,
                 dilations: tuple[int, ...] = DILATIONS, n_outputs: int = 2):
        super().__init__()
        blocks, c = [], in_channels
        for d in dilations:
            blocks.append(TemporalBlock(c, channels, kernel_size, d, dropout))
            c = channels
        self.blocks = nn.Sequential(*blocks)
        self.head = nn.Linear(channels, n_outputs)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """x: (N, C, T) -> (N, 2) from the last time step."""
        return self.head(self.blocks(x)[:, :, -1])

    def receptive_field(self) -> int:
        k = self.blocks[0].main[0].conv.kernel_size[0]
        return 1 + 2 * (k - 1) * sum(b.main[0].conv.dilation[0] for b in self.blocks)


def to_channels_first(x_ntc: torch.Tensor) -> torch.Tensor:
    """(N, T, C) protocol windows -> (N, C, T) Conv1d layout."""
    if x_ntc.ndim != 3:
        raise ValueError("expected (N, T, C)")
    return x_ntc.permute(0, 2, 1).contiguous()
