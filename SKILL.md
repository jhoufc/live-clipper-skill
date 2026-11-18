---
name: live-clipper
description: Transforma lives do YouTube (inclusive ainda ao vivo, desde o primeiro minuto, pelo DVR) em shorts verticais 9:16 prontos para TikTok, Reels e Shorts, com gancho, legenda, crédito do streamer, capa, título e descrição. Use quando a pessoa pedir para cortar, clipar ou "tirar shorts" de uma live ou transmissão longa, acompanhar lives de um lançamento, achar os melhores momentos de uma stream ou montar shorts em tela dividida (jogo em cima, rosto do streamer embaixo).
---

# Live Clipper

Pipeline local (CPU) que assiste à live no lugar da pessoa: baixa o áudio desde o início, transcreve,
encontra os momentos, baixa só os trechos em HD e monta shorts verticais com capa e descrição.
Os scripts ficam em `scripts/`, ao lado deste arquivo. Rode-os a partir da pasta de trabalho do projeto;
`livefrag.py` guarda um cache das URLs na pasta atual.

Requisitos: Python 3.10+, `ffmpeg`/`ffprobe` no PATH e `pip install -r requirements.txt`
(yt-dlp, faster-whisper, numpy, Pillow). Confira com `ffmpeg -version` e `python -c "import faster_whisper"`
antes de começar. Se faltar algo, diga o que instalar; não instale sem a pessoa pedir.

## Antes de cortar: direitos e regras da plataforma
Repostar trecho de live de outra pessoa pode gerar reivindicação de direitos ou strike, e o YouTube
não monetiza conteúdo reaproveitado sem transformação. Diga isso em uma linha e siga a decisão da pessoa.
Sempre: crédito "AO VIVO: <canal>" na tela e o link da live na descrição; edição própria (gancho, legenda,
ordem, pergunta no fim); aviso de spoiler na descrição quando mostrar história.

## Fluxo

### 1. Reconhecer as lives
Para cada link, pegue o ID e rode:
```
python scripts/livefrag.py info <video_id>
```
Isso traz o canal, o fragmento atual (`head_seq`), os segundos por fragmento (`dur_frag`, que varia entre ~1 s e ~5 s por live)
e as qualidades disponíveis. Se der "sem formatos desde o início", a live acabou: baixe o VOD com yt-dlp e pule para o passo 3.

### 2. Baixar o áudio inteiro e achar onde o conteúdo começa
```
python scripts/livefrag.py audio <id> audio/<canal>.m4a
python scripts/livefrag.py frames <id> quadros/<canal> --every 300
python scripts/contact_sheet.py --dir quadros/<canal> quadros/<canal>_folha.jpg
```
O áudio de 2 h baixa em cerca de 1 min. Abra a folha de contato: a live costuma ter pré-show (contagem regressiva, chat,
streamer falando). Anote o segundo em que o jogo começa e o layout da facecam.

### 3. Transcrever a parte que importa e medir os picos
```
ffmpeg -ss <inicio_s> -i audio/<canal>.m4a -ac 1 -ar 16000 audio/<canal>_jogo.wav
python scripts/transcribe.py audio/<canal>_jogo.wav --model base --offset <inicio_s> --out transc/<canal>.jsonl --txt transc/<canal>.txt
python scripts/peaks.py audio/<canal>.m4a --from <inicio_s>
```
Rode uma transcrição por live em paralelo, em segundo plano, com `--threads 4`. O modelo `base` roda perto de 1,5x o tempo real
num CPU de 6 núcleos; três lives ao mesmo tempo esgotam a máquina. Enquanto isso, trabalhe com o que já saiu (o `.jsonl` é incremental).
Para a live que continua, baixe depois só o pedaço novo: `audio <id> novo.m4a --from <ultimo_sq>`, com `--offset` igual a esse ponto.

### 4. Escolher os momentos
Procure no `.txt` reações ("olha", "nossa", "meu deus", "absurdo", "não acredito", "finalmente"), descobertas de mecânica,
números e viradas. Cruze com os picos de volume. Bons formatos que funcionaram:
- **o segundo exato** de um evento coletivo (lançamento, contagem regressiva) com vários streamers;
- **mecânica nova com prova na tela** (dica do jogo, menu, HUD);
- **lista de 3 detalhes**;
- **plano que deu errado** (ia na calma e virou tiroteio);
- **tour** (casa, celular, mapa).

Regras que evitam erro:
- **Só afirme o que a tela prova.** Fala sem prova ("ouvi dizer", nota de review, revelação com o jogo pausado) não vira título;
  no máximo, citação atribuída ao streamer ("ELE OUVIU QUE...").
- **Gancho no 1º segundo:** o momento mais forte vai para o começo (flash-forward), e o vídeo volta para contar como chegou lá.
- **Um loop que fecha:** o que o gancho abre, o meio ou o fim paga.

### 5. Baixar os trechos em HD e transcrever com precisão
```
python scripts/livefrag.py clip <id> brutos/<canal>_<seg>.mp4 <ini_s> <fim_s> --itag 299
python scripts/transcribe.py brutos/<canal>_<seg>.mp4 --model small --words
python scripts/contact_sheet.py brutos/<canal>_<seg>.mp4 brutos/<canal>_<seg>.jpg --every 5
```
Baixe uma janela com folga (uns 20 s antes e depois). Use a folha de contato para ver a ação e medir a facecam:
extraia um quadro inteiro (`ffmpeg -ss 10 -i trecho.mp4 -frames:v 1 q.jpg`) e anote `[x, y, w, h]` em pixels 1920x1080.
Os tempos do `.words.json` são do arquivo do trecho: use-os direto no spec.

### 6. Montar o short
Escreva `storyboard/spec.json` (modelo em `examples/spec.example.json`) e rode:
```
python scripts/build_short.py storyboard/spec.json
python scripts/qa_strip.py saida/<nome>.mp4 storyboard/qa.jpg
```
- Por trecho: `topo` (gancho na faixa de cima), `caps` (legenda escrita à mão a partir da transcrição, corrigida, em caixa alta,
  frases curtas), `credito`, e no último trecho `rodape` com o pedido de inscrição (`SEGUE O @canal`).
- O último `topo` é uma pergunta fácil de responder ("VOCÊ IA CONSEGUIR FUGIR? COMENTA").
- Duração boa: 40 a 65 s. Corte respiros e trechos sem fala.
- **Confira a tira de QA**, sempre: o rosto está inteiro? (o streamer pode mudar o layout no meio da live)
  A legenda do próprio jogo tem palavrão? (corte o trecho; não dá para cobrir). O gancho está legível?
- Números grandes (contagem regressiva): `"{\\fs190}10"` no texto da legenda.

### 7. Capa, título e descrição
```
python scripts/cover.py storyboard/capa.json
```
Modelo em `examples/capa.example.json`. Escolha para o rosto um quadro com reação forte (boca aberta, rindo, gritando):
faça uma folha só da facecam com quadros a cada 1 s e escolha o melhor.
Escreva `saida/descricao.txt` como em `examples/descricao.example.txt`:
- título em caixa alta com emoji e um alternativo;
- 2 frases de gancho e uma pergunta que puxa comentário;
- crédito e link de cada live usada;
- aviso de spoiler, quando houver;
- 3 a 5 hashtags.

### 8. Entregar
Para cada short, diga: o arquivo, o título, a duração, o gancho dos primeiros segundos, onde está o pedido de inscrição,
e o que ficou de fora e por quê (falta de prova, palavrão, direito). Os vídeos não são publicados por esta skill.

## Referência rápida dos scripts
| Script | Faz |
|---|---|
| `livefrag.py info/audio/clip/frames` | Acesso ao DVR da live por fragmento |
| `transcribe.py` | Whisper local: `base` para live, `small --words` para legenda |
| `peaks.py` | Picos de volume acima da mediana de 2 min |
| `contact_sheet.py` | Folha de quadros de um vídeo ou de uma pasta |
| `build_short.py` | Short 9:16 a partir do spec (ffmpeg + ASS) |
| `cover.py` | Capa 1080x1920 |
| `qa_strip.py` | Tira de conferência do short |

---
Autor: Jonathan Ferreira (@ojonathania no YouTube · @ojonathan.ia no TikTok e Instagram) · https://github.com/jhoufc/live-clipper-skill
