#!/usr/bin/env python3
"""livefrag: baixa partes do DVR de uma live do YouTube pelo número do fragmento (sq).

O yt-dlp não aceita --download-sections em lives "desde o início". Este script pede os
fragmentos direto (url_base + &sq=N) e lê o último fragmento no cabeçalho X-Head-Seqnum.

Comandos:
  info   <video_id>                                   canal, título, fragmento atual e segundos por fragmento
  audio  <video_id> <saida.m4a> [--from SQ] [--to SQ]  áudio da live inteira (ou de um intervalo de fragmentos)
  clip   <video_id> <saida.mp4> <ini_s> <fim_s> [--itag 299]
                                                      trecho em HD; ini/fim em segundos desde o início da live
  frames <video_id> <pasta> [--every 300] [--itag 134] [--to S]
                                                      um quadro a cada N s, para achar onde o jogo começa

Itags úteis: 140 = áudio AAC; 134 = 360p; 298 = 720p60; 299 = 1080p60.
Cache das URLs (expiram em ~6 h): .livefrag_cache.json na pasta atual (ou $LIVEFRAG_CACHE).
"""
import argparse, json, os, subprocess, sys, tempfile, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

CACHE = os.environ.get('LIVEFRAG_CACHE', '.livefrag_cache.json')
UA = 'Mozilla/5.0'


def base_urls(vid, refresh=False):
    cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
    c = cache.get(vid)
    if c and not refresh and c['expira'] > time.time() + 600:
        return c
    import yt_dlp
    with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True, 'live_from_start': True}) as y:
        info = y.extract_info(f'https://www.youtube.com/watch?v={vid}', download=False, process=False)
    fmts = {f['format_id']: f['url'] for f in info['formats'] if f.get('is_from_start') and f.get('url')}
    if not fmts:
        sys.exit('Sem formatos "desde o início": a live terminou ou o DVR está desligado. Use o VOD com yt-dlp.')
    c = {'urls': fmts, 'expira': time.time() + 5 * 3600, 'inicio': info.get('release_timestamp'),
         'canal': info.get('channel'), 'titulo': info.get('title')}
    cache[vid] = c
    json.dump(cache, open(CACHE, 'w'))
    return c


def _get(url, tries=5):
    for t in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=30) as r:
                return r.read()
        except Exception:
            if t == tries - 1:
                raise
            time.sleep(1 + t)


def head_seq(url):
    with urllib.request.urlopen(urllib.request.Request(url, method='HEAD', headers={'User-Agent': UA}), timeout=30) as r:
        return int(r.headers['X-Head-Seqnum'])


def frag(url, sq):
    return _get(f'{url}&sq={sq}')


def baixar(url, ini, fim, saida, workers=24):
    with ThreadPoolExecutor(workers) as ex:
        partes = list(ex.map(lambda s: frag(url, s), range(ini, fim + 1)))
    with open(saida, 'wb') as f:
        for p in partes:
            f.write(p)
    return saida


def dur_frag(vid):
    """Segundos por fragmento: tempo desde o início da live / fragmento atual (varia por live: ~1 s ou ~5 s)."""
    c = base_urls(vid)
    return (time.time() - c['inicio']) / head_seq(c['urls']['140'])


def ffmpeg(*a):
    subprocess.run(['ffmpeg', '-v', 'error', '-y', *a], check=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    p = sp.add_parser('info'); p.add_argument('vid')
    p = sp.add_parser('audio'); p.add_argument('vid'); p.add_argument('saida')
    p.add_argument('--from', dest='ini', type=int, default=0); p.add_argument('--to', dest='fim', type=int)
    p = sp.add_parser('clip'); p.add_argument('vid'); p.add_argument('saida'); p.add_argument('ini', type=float); p.add_argument('fim', type=float)
    p.add_argument('--itag', default='299'); p.add_argument('--dur-frag', type=float)
    p = sp.add_parser('frames'); p.add_argument('vid'); p.add_argument('pasta')
    p.add_argument('--every', type=float, default=300); p.add_argument('--itag', default='134'); p.add_argument('--to', type=float)
    p.add_argument('--dur-frag', type=float)
    a = ap.parse_args()
    c = base_urls(a.vid)

    if a.cmd == 'info':
        print(json.dumps({'canal': c['canal'], 'titulo': c['titulo'], 'head_seq': head_seq(c['urls']['140']),
                          'dur_frag': round(dur_frag(a.vid), 3), 'itags': sorted(c['urls'])}, ensure_ascii=False))
    elif a.cmd == 'audio':
        fim = a.fim if a.fim is not None else head_seq(c['urls']['140'])
        raw = a.saida + '.raw'
        baixar(c['urls']['140'], a.ini, fim, raw)
        ffmpeg('-i', raw, '-c', 'copy', a.saida); os.remove(raw)
        print(json.dumps({'arquivo': a.saida, 'sq_ini': a.ini, 'sq_fim': fim}))
    elif a.cmd == 'clip':
        df = a.dur_frag or dur_frag(a.vid)
        s0, s1 = int(a.ini / df), int(a.fim / df) + 1
        va, aa = a.saida + '.v.raw', a.saida + '.a.raw'
        baixar(c['urls'][a.itag], s0, s1, va); baixar(c['urls']['140'], s0, s1, aa)
        ffmpeg('-i', va, '-i', aa, '-map', '0:v', '-map', '1:a', '-c', 'copy', a.saida)
        os.remove(va); os.remove(aa)
        print(json.dumps({'arquivo': a.saida, 'sq': [s0, s1], 'dur_frag': round(df, 3)}))
    elif a.cmd == 'frames':
        df = a.dur_frag or dur_frag(a.vid)
        fim = a.to if a.to is not None else head_seq(c['urls']['140']) * df
        os.makedirs(a.pasta, exist_ok=True)
        url = c['urls'][a.itag]

        def um(t):
            raw = os.path.join(tempfile.gettempdir(), f'lf_{a.vid}_{int(t)}.mp4')
            open(raw, 'wb').write(frag(url, int(t / df)))
            ffmpeg('-i', raw, '-frames:v', '1', '-vf', 'scale=320:-1', os.path.join(a.pasta, f'{int(t):05d}.jpg'))
            os.remove(raw)
        ts = []; t = 0.0
        while t <= fim: ts.append(t); t += a.every
        with ThreadPoolExecutor(16) as ex:
            list(ex.map(um, ts))
        print(json.dumps({'pasta': a.pasta, 'quadros': len(ts)}))


if __name__ == '__main__':
    main()
