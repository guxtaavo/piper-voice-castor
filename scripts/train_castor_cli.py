"""CLI de treinamento Piper com checkpoints compatíveis com GPU de 4 GB."""

import logging

import torch
from lightning.pytorch.callbacks import ModelCheckpoint

from piper.train.__main__ import VitsLightningCLI
from piper.train.vits.dataset import VitsDataModule
from piper.train.vits.lightning import VitsModel


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True
    torch.backends.cudnn.deterministic = False

    checkpoints = [
        ModelCheckpoint(
            monitor="val_mel",
            mode="min",
            save_top_k=5,
            save_last=True,
            filename="epoch={epoch}-val_mel={val_mel:.4f}",
            auto_insert_metric_name=False,
        )
    ]

    VitsLightningCLI(
        VitsModel,
        VitsDataModule,
        trainer_defaults={"max_epochs": -1, "callbacks": checkpoints},
    )


if __name__ == "__main__":
    main()
