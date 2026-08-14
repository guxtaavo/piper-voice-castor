from __future__ import annotations

import argparse
import inspect
from pathlib import Path, PosixPath

import torch

from piper.train.vits.lightning import VitsModel


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Adapta metadados de checkpoints Piper antigos ao treinador atual."
    )
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    torch.serialization.add_safe_globals([PosixPath])
    checkpoint = torch.load(args.input, map_location="cpu", weights_only=True)

    hyperparameters = checkpoint.get("hyper_parameters")
    if not isinstance(hyperparameters, dict):
        raise ValueError("O checkpoint não possui hyper_parameters válidos.")

    valid_parameters = set(inspect.signature(VitsModel.__init__).parameters)
    valid_parameters.discard("self")
    removed = sorted(set(hyperparameters) - valid_parameters - {"_instantiator"})

    checkpoint["hyper_parameters"] = {
        key: value
        for key, value in hyperparameters.items()
        if key in valid_parameters or key == "_instantiator"
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    torch.save(checkpoint, args.output)

    print(f"Checkpoint adaptado: {args.output}")
    print(f"Parâmetros removidos: {', '.join(removed) if removed else 'nenhum'}")
    print(f"Parâmetros preservados: {len(checkpoint['hyper_parameters'])}")


if __name__ == "__main__":
    main()
