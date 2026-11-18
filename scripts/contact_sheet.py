#!/usr/bin/env python3
"""contact_sheet: folha de contato com um quadro a cada N s, com o tempo marcado.

  python contact_sheet.py trecho.mp4 trecho.jpg --every 5 [--from 30 --to 90]
  python contact_sheet.py --dir quadros/ live.jpg      (junta os .jpg de livefrag.py frames)
Serve para achar onde o jogo começa, ver a ação e medir a posição da facecam.
"""
import argparse, glob, io, os, subprocess
from PIL import Image, ImageDraw


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('src', nargs='?'); ap.add_argument('out')
    ap.add_argument('--every', type=float, default=5); ap.add_argument('--from', dest='ini', type=float, default=0)
    ap.add_argument('--to', type=float); ap.add_argument('--dir'); ap.add_argument('--cols', type=int, default=6)
    a = ap.parse_args()
    W, H = 384, 216
    tiles = []
    if a.dir:
        for f in sorted(glob.glob(os.path.join(a.dir, '*.jpg'))):
            tiles.append((f'{int(os.path.basename(f)[:5]) // 60}min', Image.open(f).convert('RGB')))
    else:
        dur = float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', a.src]))
        t, fim = a.ini, a.to or dur
        while t < fim:
            b = subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(t), '-i', a.src, '-frames:v', '1', '-f', 'image2pipe',
                                '-c:v', 'mjpeg', '-'], capture_output=True).stdout
            try:
                tiles.append((f'{t:.0f}s', Image.open(io.BytesIO(b)).convert('RGB')))
            except Exception:
                pass
            t += a.every
    rows = (len(tiles) + a.cols - 1) // a.cols
    im = Image.new('RGB', (W * a.cols, H * max(1, rows)))
    for i, (lab, fr) in enumerate(tiles):
        fr = fr.resize((W, H)); d = ImageDraw.Draw(fr)
        d.rectangle([0, 0, 60, 16], fill='black'); d.text((3, 3), lab, fill='yellow')
        im.paste(fr, ((i % a.cols) * W, (i // a.cols) * H))
    im.save(a.out, quality=82)
    print('ok', a.out, len(tiles), 'quadros')


if __name__ == '__main__':
    main()
