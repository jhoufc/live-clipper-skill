#!/usr/bin/env python3
"""qa_strip: tira com N quadros igualmente espaçados de um vídeo, para conferir o short de uma olhada.

  python qa_strip.py short.mp4 short_qa.jpg [--n 9]
O que olhar: rosto inteiro no quadro de baixo (o streamer pode mudar o layout no meio da live),
legenda do próprio jogo com palavrão, texto do gancho legível, CTA no fim.
"""
import argparse, io, subprocess
from PIL import Image


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('video'); ap.add_argument('out'); ap.add_argument('--n', type=int, default=9)
    a = ap.parse_args()
    dur = float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', a.video]))
    im = Image.new('RGB', (240 * a.n, 427))
    for i in range(a.n):
        t = dur * (i + .5) / a.n
        b = subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(t), '-i', a.video, '-frames:v', '1', '-vf', 'scale=240:427',
                            '-f', 'image2pipe', '-c:v', 'mjpeg', '-'], capture_output=True).stdout
        im.paste(Image.open(io.BytesIO(b)), (i * 240, 0))
    im.save(a.out, quality=85); print('ok', a.out)


if __name__ == '__main__':
    main()
