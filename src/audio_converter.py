from __future__ import annotations

import argparse
import math
import re
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_DIR = PROJECT_ROOT / "assets" / "audios"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "assets" / "wavs"
DEFAULT_SAMPLE_RATE = 22_050


def natural_sort_key(path: Path) -> list[int | str]:
    return [
        int(part) if part.isdigit() else part.casefold()
        for part in re.split(r"(\d+)", path.name)
    ]


def find_mp3_files(input_dir: Path) -> list[Path]:
    if not input_dir.is_dir():
        raise FileNotFoundError(
            f"Pasta de áudios não encontrada: {input_dir}"
        )

    return sorted(
        (
            path
            for path in input_dir.iterdir()
            if path.is_file() and path.suffix.casefold() == ".mp3"
        ),
        key=natural_sort_key,
    )


def convert_mp3_to_wav(
    input_file: Path,
    output_file: Path,
    sample_rate: int,
) -> None:
    audio, original_sample_rate = sf.read(
        input_file,
        dtype="float32",
        always_2d=True,
    )

    if audio.size == 0:
        raise ValueError(f"O MP3 está vazio: {input_file}")

    mono_audio = np.mean(audio, axis=1, dtype=np.float32)

    if original_sample_rate != sample_rate:
        common_divisor = math.gcd(original_sample_rate, sample_rate)
        mono_audio = resample_poly(
            mono_audio,
            up=sample_rate // common_divisor,
            down=original_sample_rate // common_divisor,
        ).astype(np.float32, copy=False)

    output_file.parent.mkdir(parents=True, exist_ok=True)
    temporary_file = output_file.with_suffix(".tmp.wav")

    try:
        sf.write(
            temporary_file,
            mono_audio,
            sample_rate,
            format="WAV",
            subtype="PCM_16",
        )

        with sf.SoundFile(temporary_file) as converted_audio:
            is_valid = (
                converted_audio.format == "WAV"
                and converted_audio.subtype == "PCM_16"
                and converted_audio.channels == 1
                and converted_audio.samplerate == sample_rate
                and converted_audio.frames > 0
            )

        if not is_valid:
            raise ValueError(
                f"O WAV gerado não possui o formato esperado: "
                f"{temporary_file}"
            )

        temporary_file.replace(output_file)
    finally:
        if temporary_file.exists():
            temporary_file.unlink()


def convert_audio_folder(
    input_dir: Path,
    output_dir: Path,
    sample_rate: int,
    overwrite: bool,
) -> None:
    mp3_files = find_mp3_files(input_dir)

    if not mp3_files:
        print(f"Nenhum arquivo MP3 encontrado em: {input_dir}")
        return

    output_dir.mkdir(parents=True, exist_ok=True)
    converted_count = 0
    skipped_count = 0

    for index, mp3_file in enumerate(mp3_files, start=1):
        wav_file = output_dir / f"{mp3_file.stem}.wav"

        if wav_file.exists() and not overwrite:
            print(
                f"[{index}/{len(mp3_files)}] "
                f"{wav_file.name} já existe; pulando."
            )
            skipped_count += 1
            continue

        print(
            f"[{index}/{len(mp3_files)}] "
            f"Convertendo {mp3_file.name} -> {wav_file.name}"
        )
        convert_mp3_to_wav(
            input_file=mp3_file,
            output_file=wav_file,
            sample_rate=sample_rate,
        )
        converted_count += 1

    print(
        f"Concluído: {converted_count} convertido(s), "
        f"{skipped_count} ignorado(s)."
    )
    print(f"Arquivos WAV: {output_dir}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Converte todos os MP3 de uma pasta para WAV mono PCM de 16 bits."
        )
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=DEFAULT_INPUT_DIR,
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
    )
    parser.add_argument(
        "--sample-rate",
        type=int,
        default=DEFAULT_SAMPLE_RATE,
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.sample_rate <= 0:
        raise ValueError("--sample-rate deve ser maior que zero.")

    convert_audio_folder(
        input_dir=args.input_dir.resolve(),
        output_dir=args.output_dir.resolve(),
        sample_rate=args.sample_rate,
        overwrite=args.overwrite,
    )


if __name__ == "__main__":
    main()
