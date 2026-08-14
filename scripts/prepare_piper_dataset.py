from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepara os WAVs e o metadata.csv para treinar uma voz Piper."
    )
    parser.add_argument(
        "--phrases",
        type=Path,
        required=True,
        help="Arquivo TXT UTF-8 com uma frase por linha.",
    )
    parser.add_argument(
        "--audio-dir",
        type=Path,
        required=True,
        help="Pasta contendo audio_0.wav, audio_1.wav, etc.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Pasta Linux de destino do dataset.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    phrases_path = args.phrases.expanduser().resolve()
    source_audio_dir = args.audio_dir.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    target_audio_dir = output_dir / "audio"

    if not phrases_path.is_file():
        raise FileNotFoundError(f"Arquivo de frases não encontrado: {phrases_path}")
    if not source_audio_dir.is_dir():
        raise FileNotFoundError(f"Pasta de áudio não encontrada: {source_audio_dir}")

    phrases = [
        line.strip()
        for line in phrases_path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]
    if not phrases:
        raise ValueError("O arquivo de frases está vazio.")

    output_dir.mkdir(parents=True, exist_ok=True)
    target_audio_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "cache").mkdir(exist_ok=True)
    (output_dir / "output").mkdir(exist_ok=True)

    metadata_lines: list[str] = []
    missing: list[str] = []

    for index, phrase in enumerate(phrases):
        if "|" in phrase:
            raise ValueError(f"A frase {index} contém o delimitador '|'.")

        filename = f"audio_{index}.wav"
        source_audio = source_audio_dir / filename
        if not source_audio.is_file():
            missing.append(filename)
            continue

        shutil.copy2(source_audio, target_audio_dir / filename)
        metadata_lines.append(f"{filename}|{phrase}")

    if missing:
        preview = ", ".join(missing[:10])
        raise FileNotFoundError(
            f"Faltam {len(missing)} áudios. Primeiros arquivos: {preview}"
        )

    metadata_path = output_dir / "metadata.csv"
    metadata_path.write_text(
        "\n".join(metadata_lines) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    copied_wavs = len(list(target_audio_dir.glob("*.wav")))
    if copied_wavs != len(phrases):
        raise RuntimeError(
            f"Validação falhou: {len(phrases)} frases e {copied_wavs} WAVs."
        )

    print(f"Dataset pronto: {output_dir}")
    print(f"Frases: {len(phrases)}")
    print(f"WAVs: {copied_wavs}")
    print(f"Metadata: {metadata_path}")


if __name__ == "__main__":
    main()
