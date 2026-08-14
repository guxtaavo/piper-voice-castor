#!/usr/bin/env bash
set -euo pipefail

PIPER_DIR="/home/guxtaavo/piper1-gpl"
TRAINING_DIR="/home/guxtaavo/castor-training"
PROJECT_DIR="/mnt/c/Users/Gustavo13/Documents/GitHub/piper-voice-castor"
TRAINING_CHECKPOINT="${TRAINING_DIR}/training/lightning_logs/version_0/checkpoints/last.ckpt"
SMOKE_CHECKPOINT="${TRAINING_DIR}/smoke-test/lightning_logs/version_0/checkpoints/last.ckpt"

if [[ -n "${1:-}" ]]; then
    RESUME_CHECKPOINT="$1"
elif [[ -f "${TRAINING_CHECKPOINT}" ]]; then
    RESUME_CHECKPOINT="${TRAINING_CHECKPOINT}"
else
    RESUME_CHECKPOINT="${SMOKE_CHECKPOINT}"
fi

if [[ ! -f "${RESUME_CHECKPOINT}" ]]; then
    echo "Checkpoint não encontrado: ${RESUME_CHECKPOINT}" >&2
    exit 1
fi

cd "${PIPER_DIR}"
source .venv/bin/activate

export PYTHONPATH="${PROJECT_DIR}/scripts/piper_compat"
export PYTORCH_CUDA_ALLOC_CONF="expandable_segments:True"

python "${PROJECT_DIR}/scripts/train_castor_cli.py" fit \
    --trainer.accelerator gpu \
    --trainer.devices 1 \
    --trainer.precision 16-mixed \
    --trainer.max_epochs 6260 \
    --trainer.default_root_dir "${TRAINING_DIR}/training" \
    --trainer.log_every_n_steps 20 \
    --trainer.num_sanity_val_steps 0 \
    --data.voice_name castor \
    --data.csv_path "${TRAINING_DIR}/metadata.csv" \
    --data.audio_dir "${TRAINING_DIR}/audio" \
    --model.sample_rate 22050 \
    --model.mos_metric none \
    --data.espeak_voice pt-br \
    --data.cache_dir "${TRAINING_DIR}/cache" \
    --data.config_path "${TRAINING_DIR}/castor.onnx.json" \
    --data.batch_size 1 \
    --data.num_workers 2 \
    --data.validation_split 0.02 \
    --ckpt_path "${RESUME_CHECKPOINT}"
