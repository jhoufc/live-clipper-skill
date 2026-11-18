# Live Clipper · skill para Claude Code

Transforme lives em shorts verticais **enquanto a live ainda está rolando**.
A skill baixa o áudio da transmissão desde o primeiro minuto (pelo DVR do YouTube), transcreve,
encontra os momentos e baixa só os trechos em HD. Depois monta shorts 9:16 com:
- gancho;
- legenda;
- crédito do streamer;
- capa;
- título e descrição.

Tudo roda no seu computador, em CPU.

Criado por **Jonathan Ferreira**, engenheiro de software que constrói agentes de IA que trabalham sozinhos.
Acompanhe os próximos no [YouTube @ojonathania](https://www.youtube.com/channel/UC_6u6FagmzsU9Vvn_MVtFug),
no [TikTok @ojonathan.ia](https://www.tiktok.com/@ojonathan.ia) e no [Instagram @ojonathan.ia](https://www.instagram.com/ojonathan.ia).

> Feito em 18/11/2026, no lançamento antecipado do GTA 6: 11 shorts tirados das primeiras horas de três lives.

```
live do YouTube ──► áudio desde o início ──► transcrição + picos de volume ──► momentos escolhidos
        │                                                                          │
        └──────────────── trechos em HD (só o que importa) ◄───────────────────────┘
                                   │
                 short 9:16 (jogo em cima, rosto embaixo, legenda, gancho, CTA)
                                   │
                         capa + título + descrição + hashtags
```

## O que tem aqui
| Arquivo | Para quê |
|---|---|
| `SKILL.md` | Instruções que o Claude segue: o fluxo, as regras editoriais e os comandos |
| `scripts/livefrag.py` | Acesso ao DVR da live: `info`, `audio`, `clip`, `frames` |
| `scripts/transcribe.py` | Transcrição local com faster-whisper |
| `scripts/peaks.py` | Picos de volume (gritos, risadas, explosões) |
| `scripts/contact_sheet.py` | Folha de quadros para ver a ação e medir a facecam |
| `scripts/build_short.py` | Monta o short a partir de um `spec.json` |
| `scripts/cover.py` | Capa 1080×1920 |
| `scripts/qa_strip.py` | Tira de conferência do short pronto |
| `examples/` | Spec, capa e descrição de um short real |

## Passo a passo

### 1. Instale o que a skill usa
- **Python 3.10 ou mais novo**
- **ffmpeg** no PATH:
  - Windows: `winget install Gyan.FFmpeg`
  - macOS: `brew install ffmpeg`
  - Linux: `sudo apt install ffmpeg`
- **Dependências Python**:
  ```
  pip install -r requirements.txt
  ```
- **Claude Code** instalado e logado.

Confira:
```
ffmpeg -version
python -c "import faster_whisper, yt_dlp, PIL, numpy; print('ok')"
```

### 2. Instale a skill
Clone este repositório na pasta de skills do Claude Code.

Para todos os seus projetos:
```
git clone https://github.com/jhoufc/live-clipper-skill ~/.claude/skills/live-clipper
```
Ou só para um projeto, dentro da pasta dele:
```
git clone https://github.com/jhoufc/live-clipper-skill .claude/skills/live-clipper
```
No Windows, `~` é `C:\Users\<você>`. Abra o Claude Code de novo para ele encontrar a skill.

### 3. Fontes (opcional)
Os scripts procuram, nesta ordem:
1. a pasta `fonts/` da skill;
2. as fontes do sistema;
3. Impact, Anton ou DejaVu Sans Bold.

Para o visual dos exemplos, coloque em `fonts/` uma fonte condensada grossa. A [Anton](https://fonts.google.com/specimen/Anton) é gratuita (OFL). Depois use `"fonte_titulo": "Anton"` no spec.

### 4. Peça os cortes
Numa pasta de trabalho vazia, abra o Claude Code e peça, por exemplo:

> Tem essas três lives de GTA 6 rolando agora: https://www.youtube.com/watch?v=AAAA, https://www.youtube.com/watch?v=BBBB e https://www.youtube.com/watch?v=CCCC.
> Quero 5 shorts dos primeiros momentos de gameplay para o canal @meucanal, em português.

A skill então:
1. lê as lives;
2. baixa o áudio e acha onde o jogo começa;
3. transcreve em segundo plano;
4. propõe os momentos;
5. baixa os trechos em HD;
6. monta, confere e entrega cada short com capa e descrição.

Você pode orientar no meio do caminho: "quero mais mecânica e menos história", "esse não, tem spoiler", "troca o gancho".

### 5. Use os scripts sem o Claude (opcional)
Todos funcionam pela linha de comando (`python scripts/<nome>.py -h`). Um fluxo mínimo:
```
python scripts/livefrag.py info VIDEO_ID
python scripts/livefrag.py audio VIDEO_ID audio/live.m4a
python scripts/transcribe.py audio/live.m4a --model base --txt transc/live.txt
python scripts/peaks.py audio/live.m4a
python scripts/livefrag.py clip VIDEO_ID brutos/trecho.mp4 2760 2905
python scripts/transcribe.py brutos/trecho.mp4 --model small --words
# escreva storyboard/spec.json a partir de examples/spec.example.json
python scripts/build_short.py storyboard/spec.json
python scripts/cover.py storyboard/capa.json
python scripts/qa_strip.py saida/short.mp4 storyboard/qa.jpg
```

## Formato do spec (resumo)
```json
{
  "saida": "../saida/meu_short.mp4",
  "layouts": { "streamer": { "game": [0, 0, 1440, 1080], "face": [1640, 790, 280, 166] } },
  "segs": [
    { "src": "../brutos/trecho.mp4", "ini": 108.9, "fim": 111.6, "layout": "streamer",
      "credito": "NOME_DO_CANAL", "topo": "A POLÍCIA DO GTA 6\nNÃO ESQUECE VOCÊ",
      "caps": [[109.0, 111.6, "BOMBA DE TINTA!"]] },
    { "src": "../brutos/trecho.mp4", "ini": 124.9, "fim": 131.0, "layout": "streamer",
      "topo": "VOCÊ IA CONSEGUIR\nFUGIR? COMENTA", "rodape": "SEGUE O @SEUCANAL" }
  ]
}
```
- `game` e `face` são recortes `[x, y, largura, altura]` em pixels do vídeo de origem.
- Os tempos são em segundos do arquivo do trecho.
- Campos opcionais estão no topo de `scripts/build_short.py`: fontes, cor da legenda e fundo.

## Desempenho (Ryzen 5 5600G, 16 GB, sem placa de vídeo)
- **Áudio de 2 h de live:** cerca de 1 min para baixar.
- **Transcrição `base`:** perto de 1,5x o tempo real por live. Com três lives em paralelo, a CPU fica no limite.
- **Trecho HD de 2 min:** segundos para baixar.
- **Short de 50 s:** cerca de 30 s para montar.

## Limites conhecidos
- **Fonte:** só YouTube Live com DVR ligado. Para lives que já acabaram, use o VOD com `yt-dlp`.
- **Escolha dos momentos:** é feita pelo Claude lendo transcrição e quadros, com você aprovando. Não é um detector mágico: pico de volume sozinho não é corte.
- **Facecam:** a posição é medida por streamer. Se ele mudar o layout no meio da live, refaça a medida (a tira de QA mostra).
- **Publicação:** não é automática. A API do TikTok exige auditoria do app para postar em modo público.

## Responsabilidade
Esta skill baixa conteúdo de terceiros.
- **Direitos:** repostar trechos de lives sem autorização pode gerar reivindicação de direitos autorais ou strike e pode violar os Termos de Serviço das plataformas. Use em lives próprias, de quem autorizou ou dentro do uso transformativo permitido no seu país.
- **Crédito:** dê sempre crédito na tela e o link na descrição.

Você é responsável pelo que publica.

## Contribuir
Achou um bug, a live quebrou o `livefrag.py` ou adaptou para outro nicho (podcast, futebol, entrevista)?
Abra uma issue ou um pull request. É um projeto mantido no melhor esforço: o YouTube muda, e o truque do DVR pode parar de funcionar.

## Créditos
- **Autor:** Jonathan Ferreira, [@ojonathania](https://www.youtube.com/channel/UC_6u6FagmzsU9Vvn_MVtFug) no YouTube e [@ojonathan.ia](https://www.instagram.com/ojonathan.ia) no TikTok e no Instagram.
- **Construído com:** [Claude Code](https://claude.com/claude-code).
- **Exemplos em `examples/`:** descrevem um short feito a partir de um trecho da live do canal JOAO_PSX, em 18/11/2026, com crédito na tela e na descrição. O vídeo não faz parte deste repositório.
- **Bibliotecas:** [yt-dlp](https://github.com/yt-dlp/yt-dlp), [faster-whisper](https://github.com/SYSTRAN/faster-whisper), [FFmpeg](https://ffmpeg.org), [Pillow](https://python-pillow.org) e [NumPy](https://numpy.org).

Se esta skill te ajudou, deixe uma ⭐ e marque o @ojonathan.ia quando postar os seus cortes.

## Licença
MIT, veja `LICENSE`.
