"""Compatibilidade segura entre checkpoints antigos do Piper e PyTorch recente."""

from pathlib import PosixPath

import torch


# Checkpoints oficiais antigos do Piper armazenam caminhos pathlib.PosixPath.
# O PyTorch recente usa weights_only=True e exige que esse tipo seja liberado.
torch.serialization.add_safe_globals([PosixPath])
