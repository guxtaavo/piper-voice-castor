# Piper Voice Castor

Projeto para criar uma voz personalizada em português brasileiro com o
[Piper TTS](https://github.com/OHF-Voice/piper1-gpl).

O repositório reúne o fluxo utilizado para:

1. ler frases de um arquivo TXT;
2. gerar e baixar um MP3 para cada frase;
3. converter os MP3s para WAV no formato esperado pelo Piper;
4. preparar o dataset e o `metadata.csv`;
5. treinar ou continuar o modelo no Google Colab;
6. exportar o checkpoint para ONNX;
7. executar localmente a voz Castor treinada.

## Estrutura do projeto

```text
piper-voice-castor/
├── assets/
│   ├── audios/                  # MP3s gerados (ignorado pelo Git)
│   ├── generated/               # WAVs gerados pelo modelo
│   ├── wavs/                    # Dataset convertido (ignorado pelo Git)
│   └── frases.txt               # Uma frase por linha
├── models/
│   ├── pt_BR-castor-medium/     # Modelo Castor treinado
│   └── pt_BR-faber-medium/      # Modelo brasileiro usado como referência
├── notebooks/
│   └── colab/
│       └── piper_castor.ipynb   # Treinamento e exportação no Colab
├── scripts/
│   ├── piper_compat/            # Compatibilidade de checkpoints antigos
│   ├── prepare_piper_dataset.py # Cria metadata.csv e copia os WAVs
│   ├── sanitize_piper_checkpoint.py
│   ├── train_castor_cli.py
│   └── train_castor_wsl.sh
├── src/
│   ├── app.py                   # Experimento inicial com Selenium
│   ├── audio_converter.py       # Conversão MP3 para WAV
│   ├── phrase_generator.py      # Geração e download dos MP3s
│   └── piper_demo.py            # Demonstração local da voz Castor
├── training/                    # Dataset/checkpoints locais (ignorado pelo Git)
├── requirements.txt
└── README.md
```

## Requisitos locais

- Windows 10 ou 11;
- Python 3.12;
- Google Chrome, utilizado pelo Selenium;
- acesso à internet para gerar os MP3s;
- arquivos `.onnx` e `.onnx.json` para testar a voz localmente.

O treinamento é feito separadamente no Google Colab. Não é necessário instalar
CUDA ou as bibliotecas de treinamento no ambiente local para usar o demo.

## Instalação no Windows

No PowerShell, dentro do repositório:

```powershell
py -3.12 -m venv .venv
```

Ative o ambiente:

```powershell
.\venv\Scripts\Activate.ps1
```

Instale as dependências congeladas do ambiente local:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

O `requirements.txt` foi gerado a partir do `pip freeze` do ambiente Python 3.12
usado no projeto.

## 1. Preparar as frases

Edite [assets/frases.txt](assets/frases.txt) e coloque uma frase por linha. A
ordem das linhas define a numeração dos áudios:

```text
Olá, seja bem-vindo!
Até logo, tenha um ótimo dia.
Muito obrigado pela visita.
```

Essas linhas serão associadas a `audio_0`, `audio_1`, `audio_2` e assim por
diante. Não altere a ordem depois que os áudios forem gerados.

## 2. Gerar os MP3s

Execute:

```powershell
python src\phrase_generator.py
```

Por padrão, o script:

- lê `assets/frases.txt`;
- abre o Chrome com Selenium;
- fecha abas inesperadas abertas por anúncios;
- aguarda cada download terminar antes de avançar;
- salva os arquivos em `assets/audios/audio_N.mp3`;
- mantém um intervalo de 2 segundos entre as gerações;
- ignora arquivos que já existem.

Para gerar novamente arquivos existentes:

```powershell
python src\phrase_generator.py --overwrite
```

Para usar outro intervalo entre as frases:

```powershell
python src\phrase_generator.py --delay 5
```

## 3. Converter MP3 para WAV

Execute:

```powershell
python src\audio_converter.py
```

Os arquivos são gravados em `assets/wavs` no formato utilizado pelo treinamento:

- WAV;
- mono;
- PCM de 16 bits;
- 22.050 Hz.

Para converter novamente arquivos que já existem:

```powershell
python src\audio_converter.py --overwrite
```

## 4. Preparar o dataset do Piper

Execute:

```powershell
python scripts\prepare_piper_dataset.py `
  --phrases assets\frases.txt `
  --audio-dir assets\wavs `
  --output-dir training\castor_dataset
```

O resultado será semelhante a:

```text
training/castor_dataset/
├── audio/
│   ├── audio_0.wav
│   ├── audio_1.wav
│   └── ...
└── metadata.csv
```

Compacte o dataset para enviar ao Google Drive:

```powershell
Compress-Archive `
  -Path training\castor_dataset\* `
  -DestinationPath training\castor_dataset.zip `
  -Force
```

## 5. Treinar no Google Colab

O treinamento está documentado e automatizado no notebook:

**[Abrir o notebook de treinamento](notebooks/colab/piper_castor.ipynb)**

Antes de executá-lo:

1. envie `training/castor_dataset.zip` para
   `Meu Drive/piper-castor/castor_dataset.zip`;
2. abra o notebook no Google Colab;
3. selecione uma GPU T4 ou superior;
4. revise o bloco **Configuração central**;
5. execute as células de cima para baixo.

As opções mais importantes do notebook são:

```python
ADDITIONAL_EPOCHS = 30
BATCH_SIZE = 8
RESUME_TRAINING = True
```

Com `RESUME_TRAINING = True`, o notebook procura no Google Drive o
`last.ckpt` mais recente e continua automaticamente. O próprio notebook instala
as dependências Linux necessárias, prepara checkpoints antigos, acompanha a GPU,
exporta o ONNX e gera um WAV de teste.

Os arquivos finais ficam em:

```text
Meu Drive/piper-castor/
├── pt_BR-castor-medium.onnx
├── pt_BR-castor-medium.onnx.json
└── teste_castor.wav
```

## 6. Instalar o modelo treinado no projeto

Baixe do Google Drive os dois arquivos finais e coloque-os em:

```text
models/pt_BR-castor-medium/
├── pt_BR-castor-medium.onnx
└── pt_BR-castor-medium.onnx.json
```

Os nomes precisam permanecer iguais e os dois arquivos devem estar na mesma
pasta.

## 7. Testar a voz Castor localmente

Para gerar a frase padrão:

```powershell
python src\piper_demo.py
```

Para informar outra frase:

```powershell
python src\piper_demo.py "Olá, meu nome é Castor. Este é um teste da minha voz."
```

O áudio será salvo por padrão em:

```text
assets/generated/castor_teste.wav
```

Também é possível escolher outro destino:

```powershell
python src\piper_demo.py `
  "Esta frase será gravada em outro arquivo." `
  --output assets\generated\outro_teste.wav
```

## Continuar o treinamento

Para melhorar um modelo existente:

1. mantenha `RESUME_TRAINING = True` no notebook;
2. altere `ADDITIONAL_EPOCHS` para 30 ou 50;
3. execute novamente o fluxo no Colab;
4. compare sempre a mesma frase entre os checkpoints.

Treinar em blocos menores facilita identificar melhora ou sobreajuste. Se a voz
ficar instável ou metálica, teste também valores menores de `noise_scale` e
`noise_w_scale` no bloco de síntese do notebook.

## Observações

- `assets/audios`, `assets/wavs` e `training` não são versionados pelo Git.
- Os checkpoints do Piper são grandes; mantenha-os no Google Drive.
- O modelo ONNX e seu JSON devem sempre ser distribuídos juntos.
- A qualidade depende do alinhamento exato entre cada WAV e sua frase, além da
  quantidade de épocas.
