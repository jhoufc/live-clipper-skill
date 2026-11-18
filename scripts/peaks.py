#!/usr/bin/env python3
"""peaks: picos de volume (gritos, risadas, explosões) acima da mediana local.

  python peaks.py live.m4a --min 6 --top 40 --from 3300
Imprime "segundo mm:ss dB +acima" e grava <arquivo>.peaks.json com a curva por segundo.
Pico isolado não é corte: confira na transcrição e na imagem antes de usar.
"""
import argparse, json, subprocess
import numpy as np


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('audio'); ap.add_argument('--min', type=float, default=6, help='dB acima da mediana de 2 min')
    ap.add_argument('--top', type=int, default=40); ap.add_argument('--gap', type=int, default=45, help='distância mínima entre picos (s)')
    ap.add_argument('--from', dest='ini', type=int, default=0, help='ignorar antes deste segundo (pré-live)')
    a = ap.parse_args()
    sr = 8000
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', a.audio, '-ac', '1', '-ar', str(sr), '-f', 's16le', '-'],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    n = len(x) // sr
    db = 20 * np.log10(np.sqrt((x[:n * sr].reshape(n, sr) ** 2).mean(1)) + 1e-6)
    med = np.array([np.median(db[max(0, i - 60):i + 60]) for i in range(n)])
    exc = db - med
    picos = []
    for i in np.argsort(-exc):
        if exc[i] < a.min or len(picos) >= a.top:
            break
        if i >= a.ini and all(abs(i - p['t']) > a.gap for p in picos):
            picos.append({'t': int(i), 'db': round(float(db[i]), 1), 'acima': round(float(exc[i]), 1)})
    picos.sort(key=lambda p: p['t'])
    for p in picos:
        print(f"{p['t']:6d}  {p['t'] // 60:3d}:{p['t'] % 60:02d}  {p['db']:6.1f} dB  +{p['acima']}")
    json.dump({'dur': n, 'db': [round(float(v), 1) for v in db], 'picos': picos},
              open(a.audio.rsplit('.', 1)[0] + '.peaks.json', 'w'))


if __name__ == '__main__':
    main()
