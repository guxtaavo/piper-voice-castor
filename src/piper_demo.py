from __future__ import annotations

import argparse
import json
import wave
from pathlib import Path


VOICE_NAME = "pt_BR-castor-medium"
TEXT_DEFAULT = "Digite aqui a sua frase para teste..."

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR_DEFAULT = PROJECT_ROOT / "models" / VOICE_NAME
OUTPUT_DEFAULT = PROJECT_ROOT / "assets" / "generated" / "castor_teste.wav"


def ensure_voice_files(model_dir: Path) -> tuple[Path, Path]:
    model_path = model_dir / f"{VOICE_NAME}.onnx"
    config_path = model_dir / f"{VOICE_NAME}.onnx.json"

    missing_files = [
        path for path in (model_path, config_path) if not path.is_file()
    ]
    if missing_files:
        missing_names = "\n".join(f"  - {path}" for path in missing_files)
        raise FileNotFoundError(
            "Arquivos da voz Castor não encontrados:\n"
            f"{missing_names}\n\n"
            "Baixe do Google Drive os arquivos .onnx e .onnx.json "
            f"e coloque-os em:\n  {model_dir}"
        )

    if model_path.stat().st_size < 1_000_000:
        raise OSError(f"O modelo ONNX parece inválido: {model_path}")

    with config_path.open(encoding="utf-8") as config_file:
        json.load(config_file)

    return model_path, config_path


def synthesize(
    text: str,
    model_dir: Path,
    output_path: Path,
) -> None:
    try:
        from piper import PiperVoice
    except ModuleNotFoundError as error:
        raise SystemExit(
            "Piper não está instalado neste ambiente.\n"
            "Execute: python -m pip install piper-tts"
        ) from error

    model_path, config_path = ensure_voice_files(model_dir)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Carregando a voz {VOICE_NAME}...")
    voice = PiperVoice.load(
        str(model_path),
        config_path=str(config_path),
    )

    print(f'Sintetizando: "{text}"')
    with wave.open(str(output_path), "wb") as wav_file:
        voice.synthesize_wav(text, wav_file)

    print(f"Áudio criado com sucesso: {output_path}")

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Gera um WAV em português com a voz Castor treinada."
    )
    parser.add_argument(
        "text",
        nargs="?",
        default=TEXT_DEFAULT,
        help=f'Texto falado (padrão: "{TEXT_DEFAULT}").',
    )
    parser.add_argument(
        "--model-dir",
        type=Path,
        default=MODEL_DIR_DEFAULT,
        help=f"Pasta do modelo (padrão: {MODEL_DIR_DEFAULT}).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_DEFAULT,
        help=f"Arquivo WAV de saída (padrão: {OUTPUT_DEFAULT}).",
    )
    parser.add_argument(
        "--play",
        action="store_true",
        help="Reproduz o WAV após a geração no Windows.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    text = args.text.strip()

    output_path = args.output.resolve()
    synthesize(
        text=text,
        model_dir=args.model_dir.resolve(),
        output_path=output_path,
    )

if __name__ == "__main__":
    main()
