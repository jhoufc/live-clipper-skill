#!/usr/bin/env python3
"""transcribe: transcreve áudio/vídeo com faster-whisper (CPU).

Dois usos:
  1) Live longa, para achar momentos (rápido):
       python transcribe.py live.wav --model base --offset 3300 --out live.jsonl --txt live.txt
     --offset soma o segundo da live em que o arquivo começa: o .txt sai com o tempo absoluto da live.
  2) Trecho curto, para legenda (preciso, com tempo por palavra):
       python transcribe.py clip.mp4 --model small --words
     -> clip.words.json + clip.txt ao lado do arquivo.

Dica: corte o áudio só da parte jogada antes (ffmpeg -ss <inicio> -i audio.m4a -ac 1 -ar 16000 jogo.wav).
"""
import argparse, json, os
from faster_whisper import WhisperModel


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('inputs', nargs='+')
    ap.add_argument('--model', default='base', help='tiny, base, small, medium (CPU: base para live, small para clipe)')
    ap.add_argument('--lang', default='pt')
    ap.add_argument('--threads', type=int, default=4)
    ap.add_argument('--words', action='store_true', help='tempo por palavra (para legenda)')
    ap.add_argument('--offset', type=float, default=0, help='segundo da live em que o arquivo começa')
    ap.add_argument('--out', help='jsonl incremental (só com um arquivo de entrada)')
    ap.add_argument('--txt', help='texto "segundo frase" com tempo absoluto')
    a = ap.parse_args()
    m = WhisperModel(a.model, device='cpu', compute_type='int8', cpu_threads=a.threads)
    for f in a.inputs:
        base = os.path.splitext(f)[0]
        segs, _ = m.transcribe(f, language=a.lang, vad_filter=True, beam_size=1 if not a.words else 5,
                               word_timestamps=a.words, condition_on_previous_text=False)
        jl = open(a.out, 'a', encoding='utf8') if a.out else None
        txt = open(a.txt or base + '.txt', 'w', encoding='utf8')
        words = []
        for s in segs:
            ini, fim = round(s.start + a.offset, 2), round(s.end + a.offset, 2)
            row = {'ini': ini, 'fim': fim, 'txt': s.text.strip()}
            if a.words:
                row['w'] = [[round(w.start + a.offset, 2), round(w.end + a.offset, 2), w.word.strip()] for w in s.words]
                words.append(row)
            if jl:
                jl.write(json.dumps(row, ensure_ascii=False) + '\n'); jl.flush()
            txt.write(f"{ini:8.1f} {row['txt']}\n"); txt.flush()
        if a.words:
            json.dump(words, open(base + '.words.json', 'w', encoding='utf8'), ensure_ascii=False)
        print('ok', f)


if __name__ == '__main__':
    main()
