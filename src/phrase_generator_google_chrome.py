from __future__ import annotations

import argparse
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


READLOUD_URL = (
    "https://readloud.net/portuguese/brasilian/"
    "46-voz-masculina-ricardo.html"
)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PHRASES_FILE = PROJECT_ROOT / "assets" / "frases.txt"
DEFAULT_AUDIO_DIR = PROJECT_ROOT / "assets" / "audios"
DOWNLOAD_LINK_SELECTOR = 'a[href^="/tmp/"][href$=".mp3"]'


def create_driver(
    download_dir: Path,
    browser: str = "chrome",
) -> webdriver.Remote:
    download_dir.mkdir(parents=True, exist_ok=True)

    if browser == "firefox":
        options = webdriver.FirefoxOptions()
        options.set_preference("browser.download.folderList", 2)
        options.set_preference("browser.download.dir", str(download_dir.resolve()))
        options.set_preference("browser.download.useDownloadDir", True)
        options.set_preference("dom.disable_open_during_load", True)
        options.set_preference("permissions.default.desktop-notification", 2)
        return webdriver.Firefox(options=options)

    if browser != "chrome":
        raise ValueError(f"Navegador não suportado: {browser}")

    options = webdriver.ChromeOptions()

    # O ChromeDriver normalmente desativa o bloqueador de pop-ups. Remover esse
    # switch mantém o bloqueador nativo do Chrome ativo.
    options.add_experimental_option(
        "excludeSwitches",
        ["disable-popup-blocking"],
    )
    options.add_experimental_option(
        "prefs",
        {
            "download.default_directory": str(download_dir.resolve()),
            "download.directory_upgrade": True,
            "download.prompt_for_download": False,
            "profile.default_content_setting_values.automatic_downloads": 1,
            "profile.default_content_setting_values.notifications": 2,
            "profile.default_content_setting_values.popups": 2,
            "safebrowsing.enabled": True,
        },
    )

    return webdriver.Chrome(options=options)


def read_phrases(phrases_file: Path) -> list[str]:
    if not phrases_file.is_file():
        raise FileNotFoundError(
            f"Arquivo de frases não encontrado: {phrases_file}"
        )

    phrases = [
        line.strip()
        for line in phrases_file.read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]

    if not phrases:
        raise ValueError(f"Nenhuma frase encontrada em: {phrases_file}")

    return phrases


def close_unexpected_tabs(
    driver: webdriver.Remote,
    main_window: str,
) -> None:
    """Fecha abas abertas por anúncios e retorna à aba principal."""
    for window_handle in driver.window_handles:
        if window_handle == main_window:
            continue

        driver.switch_to.window(window_handle)
        driver.close()

    driver.switch_to.window(main_window)


def is_mp3_file(file_path: Path) -> bool:
    with file_path.open("rb") as audio_file:
        signature = audio_file.read(3)

    return (
        signature == b"ID3"
        or (
            len(signature) >= 2
            and signature[0] == 0xFF
            and signature[1] & 0xE0 == 0xE0
        )
    )


def download_mp3(
    driver: webdriver.Remote,
    download_url: str,
    output_file: Path,
    timeout: float,
    retries: int,
) -> None:
    """Baixa o MP3 diretamente, sem depender do gerenciador do navegador."""
    temporary_file = output_file.with_suffix(".mp3.part")
    cookies = "; ".join(
        f"{cookie['name']}={cookie['value']}"
        for cookie in driver.get_cookies()
    )
    user_agent = driver.execute_script("return navigator.userAgent;")

    request = Request(
        download_url,
        headers={
            "Cookie": cookies,
            "Referer": driver.current_url,
            "User-Agent": user_agent,
        },
    )

    for attempt in range(1, retries + 1):
        try:
            if temporary_file.exists():
                temporary_file.unlink()

            with (
                urlopen(request, timeout=timeout) as response,
                temporary_file.open("wb") as destination,
            ):
                if response.status != 200:
                    raise OSError(
                        f"O servidor respondeu com HTTP {response.status}."
                    )

                while chunk := response.read(64 * 1024):
                    destination.write(chunk)

            if temporary_file.stat().st_size == 0:
                raise OSError("O servidor retornou um arquivo vazio.")
            if not is_mp3_file(temporary_file):
                raise OSError(
                    "O conteúdo recebido não parece ser um arquivo MP3."
                )

            temporary_file.replace(output_file)
            return
        except (HTTPError, URLError, OSError, TimeoutError) as error:
            if temporary_file.exists():
                temporary_file.unlink()

            if attempt == retries:
                raise OSError(
                    f"Falha ao baixar o MP3 após {retries} tentativa(s): "
                    f"{download_url}"
                ) from error

            retry_delay = min(2**attempt, 10)
            print(
                f"Download falhou ({attempt}/{retries}); "
                f"nova tentativa em {retry_delay}s..."
            )
            time.sleep(retry_delay)


def generate_and_download(
    driver: webdriver.Remote,
    phrase: str,
    output_file: Path,
    timeout: float,
    retries: int,
) -> None:
    wait = WebDriverWait(driver, timeout)
    main_window = driver.current_window_handle

    close_unexpected_tabs(driver, main_window)

    text_area = wait.until(
        EC.presence_of_element_located((By.NAME, "but1"))
    )
    text_area.clear()
    text_area.send_keys(phrase)

    submit_button = wait.until(
        EC.presence_of_element_located((By.NAME, "butt0"))
    )

    # Envia sem clique físico, impedindo que um overlay receba o clique.
    driver.execute_script(
        "arguments[0].form.requestSubmit(arguments[0]);",
        submit_button,
    )

    # A geração responde com um novo documento. Esperar o campo antigo ficar
    # obsoleto garante que não reutilizaremos o link do áudio anterior.
    wait.until(EC.staleness_of(text_area))
    download_link = wait.until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, DOWNLOAD_LINK_SELECTOR)
        )
    )
    close_unexpected_tabs(driver, main_window)

    download_url = download_link.get_attribute("href")
    if not download_url:
        raise OSError("O link gerado não possui uma URL de download.")

    # Baixar diretamente evita o bloqueio do navegador após vários downloads
    # automáticos consecutivos.
    download_mp3(
        driver=driver,
        download_url=download_url,
        output_file=output_file,
        timeout=timeout,
        retries=retries,
    )

    if not output_file.is_file() or output_file.stat().st_size == 0:
        raise OSError(f"O MP3 baixado é inválido: {output_file}")

    close_unexpected_tabs(driver, main_window)


def process_phrases(
    phrases_file: Path,
    audio_dir: Path,
    delay: float,
    timeout: float,
    retries: int,
    overwrite: bool,
    browser: str = "chrome",
) -> None:
    phrases = read_phrases(phrases_file)
    audio_dir.mkdir(parents=True, exist_ok=True)
    driver = create_driver(audio_dir, browser=browser)

    try:
        driver.get(READLOUD_URL)

        for index, phrase in enumerate(phrases):
            output_file = audio_dir / f"audio_{index}.mp3"

            if output_file.exists() and not overwrite:
                print(
                    f"[{index + 1}/{len(phrases)}] "
                    f"{output_file.name} já existe; pulando."
                )
                continue

            if output_file.exists():
                output_file.unlink()

            print(
                f"[{index + 1}/{len(phrases)}] "
                f"Gerando: {phrase}"
            )
            generate_and_download(
                driver=driver,
                phrase=phrase,
                output_file=output_file,
                timeout=timeout,
                retries=retries,
            )
            print(f"Salvo com sucesso: {output_file}")

            # A próxima geração somente chega aqui após o MP3 estar completo.
            if delay > 0 and index < len(phrases) - 1:
                time.sleep(delay)
    finally:
        try:
            driver.quit()
        except WebDriverException:
            # O driver pode já ter encerrado após Ctrl+C ou falha externa.
            pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Gera e baixa um MP3 para cada linha do arquivo de frases."
    )
    parser.add_argument(
        "--phrases-file",
        type=Path,
        default=DEFAULT_PHRASES_FILE,
        help=f"Arquivo TXT (padrão: {DEFAULT_PHRASES_FILE})",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_AUDIO_DIR,
        help=f"Pasta dos MP3 (padrão: {DEFAULT_AUDIO_DIR})",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Espera adicional após cada download, em segundos (padrão: 2).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=90.0,
        help="Limite por geração/download, em segundos (padrão: 90).",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=3,
        help="Tentativas de download por frase (padrão: 3).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Gera novamente os arquivos audio_N.mp3 que já existem.",
    )
    return parser.parse_args()


def main(browser: str = "chrome") -> None:
    args = parse_args()

    if args.delay < 0:
        raise ValueError("--delay não pode ser negativo.")
    if args.timeout <= 0:
        raise ValueError("--timeout deve ser maior que zero.")
    if args.retries <= 0:
        raise ValueError("--retries deve ser maior que zero.")

    process_phrases(
        phrases_file=args.phrases_file.resolve(),
        audio_dir=args.output_dir.resolve(),
        delay=args.delay,
        timeout=args.timeout,
        retries=args.retries,
        overwrite=args.overwrite,
        browser=browser,
    )


if __name__ == "__main__":
    main()
