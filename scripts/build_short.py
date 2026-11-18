#!/usr/bin/env python3
"""build_short: monta um short 9:16 a partir de trechos de lives (ffmpeg + legenda ASS).

  python build_short.py spec.json

Layout 1080x1920: faixa do gancho (0-300), jogo (300-1110), facecam do streamer (1110-1750),
rodapé livre para a interface do app. A legenda fica na emenda entre jogo e rosto, e cada trecho
leva o crédito "AO VIVO: <canal>". Veja examples/spec.example.json.

Campos do spec:
  saida            caminho do mp4 final
  layouts          {"nome": {"game": [x,y,w,h], "face": [x,y,w,h]}}  em pixels do vídeo de origem
  segs[]           {src, ini, fim, layout, credito, topo, caps: [[ini_src, fim_src, "TEXTO"]], rodape}
                   ini/fim/caps em segundos do arquivo de origem; "\\N" quebra linha no ASS; "{\\fs190}" aumenta a fonte
  fonts_dir        (opcional) pasta com as fontes; padrão: ./fonts da skill, depois a pasta de fontes do sistema
  fonte_titulo     (opcional, padrão "Impact")    fonte do gancho, da legenda e do rodapé
  fonte_credito    (opcional, padrão "Arial")
  cor_legenda      (opcional, padrão "&H0000F0FF" = amarelo, formato ASS &HAABBGGRR)
  fundo            (opcional, padrão "0x0d0b1a")
"""
import json, os, shutil, subprocess, sys, tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))


def ts(t):
    return f'{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}'


def esc(s):
    return s.replace('\n', '\\N')


def achar_fontes(spec):
    for d in [spec.get('fonts_dir'), os.path.join(AQUI, '..', 'fonts'), 'C:/Windows/Fonts',
              '/usr/share/fonts', '/Library/Fonts', '/System/Library/Fonts']:
        if d and os.path.isdir(d) and os.listdir(d):
            return os.path.abspath(d)
    return None


def caminho_filtro(p, cwd):
    """Caminho para o filtro ass do ffmpeg: relativo quando dá (evita escapar 'C:')."""
    try:
        return os.path.relpath(p, cwd).replace('\\', '/')
    except ValueError:
        return p.replace('\\', '/').replace(':', '\\:')


def main():
    spec = json.load(open(sys.argv[1], encoding='utf8'))
    base = os.path.dirname(os.path.abspath(sys.argv[1]))
    rel = lambda p: p if os.path.isabs(p) else os.path.join(base, p)
    out = os.path.abspath(rel(spec['saida']))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    bg = spec.get('fundo', '0x0d0b1a')
    ft, fc, cap_cor = spec.get('fonte_titulo', 'Impact'), spec.get('fonte_credito', 'Arial'), spec.get('cor_legenda', '&H0000F0FF')
    tmp = tempfile.mkdtemp(prefix='short_', dir=os.path.dirname(out))
    partes, t0, ev = [], 0.0, []
    try:
        for i, s in enumerate(spec['segs']):
            L = spec['layouts'][s['layout']]
            gx, gy, gw, gh = L['game']; fx, fy, fw, fh = L['face']
            dur = s['fim'] - s['ini']
            p = os.path.join(tmp, f'p{i:02d}.mp4')
            fcx = (f"[0:v]fps=30,split[a][b];"
                   f"[a]crop={gw}:{gh}:{gx}:{gy},scale=1080:810:force_original_aspect_ratio=increase,crop=1080:810[g];"
                   f"[b]crop={fw}:{fh}:{fx}:{fy},scale=1080:640:force_original_aspect_ratio=increase,crop=1080:640[f];"
                   f"color=c={bg}:s=1080x1920:r=30:d={dur}[bg];"
                   f"[bg][g]overlay=0:300[t1];[t1][f]overlay=0:1110,format=yuv420p[v];"
                   f"[0:a]aresample=48000,loudnorm=I=-15:TP=-1.5:LRA=11[au]")
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(s['ini']), '-t', str(dur), '-i', rel(s['src']),
                            '-filter_complex', fcx, '-map', '[v]', '-map', '[au]', '-c:v', 'libx264', '-preset', 'veryfast',
                            '-crf', '19', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', p], check=True)
            real = float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', p]))
            a, b = t0, t0 + real
            if s.get('topo'):
                ev.append(f"Dialogue: 1,{ts(a)},{ts(b)},Topo,,0,0,0,,{esc(s['topo'])}")
            if s.get('credito'):
                ev.append(f"Dialogue: 1,{ts(a)},{ts(b)},Cred,,0,0,0,,{{\\pos(30,1130)}}{spec.get('rotulo_credito', 'AO VIVO')}: {esc(s['credito'])}")
            if s.get('rodape'):
                ev.append(f"Dialogue: 2,{ts(a)},{ts(b)},Rod,,0,0,0,,{{\\fad(150,0)}}{esc(s['rodape'])}")
            for ci, cf, txt in s.get('caps', []):
                ca, cb = max(a, a + ci - s['ini']), min(b, a + cf - s['ini'])
                if cb > ca:
                    ev.append(f"Dialogue: 3,{ts(ca)},{ts(cb)},Cap,,0,0,0,,{{\\fscx80\\fscy80\\t(0,90,\\fscx100\\fscy100)}}{esc(txt)}")
            partes.append(p); t0 = b
        open(os.path.join(tmp, 'lista.txt'), 'w').write(''.join(f"file '{os.path.basename(p)}'\n" for p in partes))
        open(os.path.join(tmp, 'leg.ass'), 'w', encoding='utf8').write(f"""[Script Info]
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Topo,{ft},84,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,1,0,1,6,0,8,50,50,50,1
Style: Cap,{ft},92,{cap_cor},&H000000FF,&H00000000,&H64000000,0,0,0,0,100,100,1,0,1,7,3,2,50,50,800,1
Style: Cred,{fc},34,&H00FFFFFF,&H000000FF,&H00000000,&HB4000000,1,0,0,0,100,100,0,0,3,10,0,7,30,30,0,1
Style: Rod,{ft},78,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,1,0,1,6,0,2,50,50,200,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" + '\n'.join(ev) + '\n')
        fontes = achar_fontes(spec)
        vf = 'ass=leg.ass' + (f':fontsdir={caminho_filtro(fontes, tmp)}' if fontes else '')
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', 'lista.txt', '-vf', vf,
                        '-c:v', 'libx264', '-preset', 'medium', '-crf', '20', '-c:a', 'copy', '-movflags', '+faststart', out],
                       check=True, cwd=tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print('ok', out, f'{t0:.1f}s')


if __name__ == '__main__':
    main()
