#!/usr/bin/env python3
"""cover: capa 1080x1920 no molde "degradê + título + cena do jogo + rosto do streamer".

  python cover.py capa.json

capa.json:
  saida     caminho do png
  linhas    [["TEXTO", "#ffffff", tamanho], ...]  (o tamanho encolhe sozinho se não couber)
  cena      {"src": mp4, "t": segundos, "crop": [x,y,w,h]}  quadro do jogo (faixa do meio)
  rosto     {"src": mp4, "t": segundos, "crop": [x,y,w,h]}  facecam (escolha um quadro com reação forte)
  credito   (opcional) "NOME DO CANAL"
  cores     (opcional) {"topo": "#2a0a3d", "meio": "#7a1550", "base": "#ff8a3d", "faixa": "#ff3ea5"}
  fonte     (opcional) caminho de um .ttf; padrão: fonts/ da skill, Impact, Anton ou DejaVu Sans Bold
"""
import glob, io, json, os, subprocess, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont

AQUI = os.path.dirname(os.path.abspath(__file__))
W, H = 1080, 1920


def fonte(c, nomes):
    cands = [c.get('fonte')] + [p for n in nomes for p in (
        glob.glob(os.path.join(AQUI, '..', 'fonts', n)) + glob.glob(f'C:/Windows/Fonts/{n}') +
        glob.glob(f'/usr/share/fonts/**/{n}', recursive=True) + glob.glob(f'/Library/Fonts/{n}'))]
    for p in cands:
        if p and os.path.exists(p):
            return p
    sys.exit('Nenhuma fonte encontrada: coloque um .ttf em fonts/ ou passe "fonte" no json.')


def hexrgb(h):
    h = h.lstrip('#'); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def quadro(src, t, crop):
    b = subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(t), '-i', src, '-frames:v', '1', '-f', 'image2pipe', '-c:v', 'png', '-'],
                       capture_output=True, check=True).stdout
    x, y, w, h = crop
    return Image.open(io.BytesIO(b)).convert('RGB').crop((x, y, x + w, y + h))


def cobrir(im, w, h):
    r = max(w / im.width, h / im.height)
    im = im.resize((round(im.width * r), round(im.height * r)), getattr(Image, "Resampling", Image).LANCZOS)
    x, y = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((x, y, x + w, y + h))


def main():
    c = json.load(open(sys.argv[1], encoding='utf8'))
    base = os.path.dirname(os.path.abspath(sys.argv[1]))
    rel = lambda p: p if os.path.isabs(p) else os.path.join(base, p)
    cor = {'topo': '#2a0a3d', 'meio': '#7a1550', 'base': '#ff8a3d', 'faixa': '#ff3ea5', **c.get('cores', {})}
    bg = Image.new('RGB', (W, H)); d = ImageDraw.Draw(bg)
    stops = [(0, hexrgb(cor['topo'])), (.55, hexrgb(cor['meio'])), (1, hexrgb(cor['base']))]
    for y in range(H):
        f = y / H
        for (a, ca), (b, cb) in zip(stops, stops[1:]):
            if a <= f <= b:
                k = (f - a) / (b - a); col = tuple(round(ca[i] + (cb[i] - ca[i]) * k) for i in range(3))
        d.line([(0, y), (W, y)], fill=col)
    # título inclinado com contorno preto
    ft = fonte(c, ['impact.ttf', 'Impact.ttf', 'Anton-Regular.ttf', 'DejaVuSans-Bold.ttf'])
    camada = Image.new('RGBA', (W, 740), (0, 0, 0, 0)); dl = ImageDraw.Draw(camada)
    blocos = []
    for txt, cr, tam in c['linhas']:
        f = ImageFont.truetype(ft, tam)
        while f.getlength(txt) > W - 90 and tam > 40:
            tam -= 4; f = ImageFont.truetype(ft, tam)
        blocos.append((txt, cr, f, tam))
    y = 40 + max(0, (700 - sum(int(t * 1.05) for *_, t in blocos)) // 2)
    for txt, cr, f, tam in blocos:
        x = (W - f.getlength(txt)) / 2; sw = max(6, tam // 9)
        dl.text((x, y + tam // 14), txt, font=f, fill=(0, 0, 0, 150), stroke_width=sw, stroke_fill=(0, 0, 0, 150))
        dl.text((x, y), txt, font=f, fill=cr, stroke_width=sw, stroke_fill='black')
        y += int(tam * 1.05)
    camada = camada.rotate(3, resample=getattr(Image, "Resampling", Image).BICUBIC, center=(W / 2, 370))
    bg.paste(camada, (0, 0), camada)
    # cena do jogo entre faixas e rosto embaixo
    y0, y1 = 760, 1340
    bg.paste(cobrir(quadro(rel(c['cena']['src']), c['cena']['t'], c['cena']['crop']), W, y1 - y0), (0, y0))
    d.rectangle([0, y0 - 10, W, y0], fill=cor['faixa']); d.rectangle([0, y1, W, y1 + 10], fill=cor['faixa'])
    rosto = cobrir(quadro(rel(c['rosto']['src']), c['rosto']['t'], c['rosto']['crop']), W, H - y1 - 10)
    bg.paste(rosto.filter(ImageFilter.UnsharpMask(radius=2, percent=80, threshold=2)), (0, y1 + 10))
    if c.get('credito'):
        fc = ImageFont.truetype(fonte(c, ['arialbd.ttf', 'Arial Bold.ttf', 'DejaVuSans-Bold.ttf']), 34)
        t = f"{c.get('rotulo_credito', 'AO VIVO')}: {c['credito']}"
        d.rectangle([24, y1 + 30, 24 + fc.getlength(t) + 32, y1 + 86], fill=(0, 0, 0)); d.text((40, y1 + 38), t, font=fc, fill='white')
    out = rel(c['saida']); os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    bg.save(out); print('ok', out)


if __name__ == '__main__':
    main()
