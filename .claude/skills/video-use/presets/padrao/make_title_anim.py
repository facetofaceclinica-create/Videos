#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PRESET "padrão" — título elegante do GANCHO (surge de trás da cabeça, esq->dir).
=================================================================================
Gera a sequência de PNGs RGBA  edit/behind/title_anim/t_%04d.png  que o build.py compõe
ATRÁS do recorte da pessoa (efeito "texto atrás do apresentador"). Layout: duas linhas
finas (Montserrat, creme, contorno preto) com uma PALAVRA em destaque no meio (EB Garamond
Italic, dourado). O bloco inteiro desliza no eixo X (de trás da cabeça) e para totalmente
visível, com fade-in/out.

FLUXO COMPLETO DO GANCHO (fazer 1x por vídeo, ver PADRAO.md §Gancho):
  1. Extrair os frames do gancho (seg00) do vídeo base -> edit/behind/frames/f_%04d.png
  2. rembg (u2net_human_seg) em cada frame -> recorte RGBA da pessoa
  3. Trocar a COR do recorte pela versão RETOCADA (frames de base_retouched) mantendo o
     alpha do rembg -> edit/behind/fg/f_%04d.png   (senão o rosto do gancho fica sem retoque)
  4. Rodar ESTE script -> edit/behind/title_anim/t_%04d.png
  5. build.py compõe: fundo -> title_anim -> fg (pessoa) por cima.

Uso:  VIDEO_EDIT_DIR=/caminho/edit  python3 make_title_anim.py
Requer: pillow, numpy. Fontes (apt): fonts-ebgaramond, fonts-montserrat.
"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os, numpy as np
from pathlib import Path

EDIT=Path(os.environ.get("VIDEO_EDIT_DIR","/home/user/Videos/edit"))
OUTDIR=EDIT/"behind"/"title_anim"; OUTDIR.mkdir(parents=True,exist_ok=True)

# ===== PRESET "padrão" — estilo do título (não alterar p/ manter o padrão) =====
W,H=1080,1920
MONT="/usr/share/fonts/opentype/montserrat/Montserrat-Medium.otf"    # linhas finas
ITA ="/usr/share/fonts/opentype/ebgaramond/EBGaramond12-Italic.otf"  # palavra de destaque
GOLD=(201,160,70,255); CREAM=(248,244,236,255)
Y0,BIG=548,212                          # Y do topo do bloco | tamanho da palavra dourada
LEFT_TARGET=430; MAXW=615               # borda esq final (logo depois da cabeça) | largura máx das finas
SLIDE=250; SDUR=0.85; FIN=0.30; FOUT=0.40   # deslize X | duração do deslize | fade-in | fade-out
N=86; FPS=30                            # nº de frames do gancho (= duração seg00 * FPS, ~2.87s)
# ================================================================================

# ▼▼▼ PER-VIDEO — troque só o TEXTO do gancho ▼▼▼
SMALL_TOP = "como eu deixei a minha"   # linha fina de cima (creme)
HIGHLIGHT = "noiva"                    # palavra em destaque (dourado, EB Garamond Italic)
SMALL_BOT = "ainda mais bonita"        # linha fina de baixo (creme)
# ▲▲▲ FIM PER-VIDEO ▲▲▲

d0=ImageDraw.Draw(Image.new("RGBA",(W,H)))
smalls=[SMALL_TOP,SMALL_BOT]
SM=66
while SM>30:                           # auto-ajusta a fonte fina p/ caber em MAXW
    f=ImageFont.truetype(MONT,SM)
    if max(d0.textlength(t,font=f) for t in smalls)<=MAXW: break
    SM-=1
f_small=ImageFont.truetype(MONT,SM); f_big=ImageFont.truetype(ITA,BIG)
STROKE=max(2,round(SM/16))             # contorno preto leve nas linhas finas
print(f"Montserrat SM={SM} stroke={STROKE}")
lines=[(SMALL_TOP,f_small,CREAM,STROKE),
       (HIGHLIGHT,f_big,GOLD,0),
       (SMALL_BOT,f_small,CREAM,STROKE)]
def bb(txt,f,sw): return d0.textbbox((0,0),txt,font=f,stroke_width=sw)
maxw=max((bb(t,f,sw)[2]-bb(t,f,sw)[0]) for t,f,c,sw in lines)
CX=int(LEFT_TARGET+maxw/2)
base=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(base)
sh =Image.new("RGBA",(W,H),(0,0,0,0)); ds=ImageDraw.Draw(sh)
pos=[]; y=Y0; minx=W; maxx=0
for txt,f,col,sw in lines:
    b=bb(txt,f,sw); wln=b[2]-b[0]; h=b[3]-b[1]
    x=CX-wln//2-b[0]; yy=y-b[1]; pos.append((x,yy,txt,f,col,sw)); y+=h+16
    minx=min(minx,x+b[0]); maxx=max(maxx,x+b[2])
# sombra suave só na palavra dourada (legibilidade sobre fundo claro)
for x,yy,txt,f,col,sw in pos:
    if sw==0: ds.text((x+3,yy+4),txt,font=f,fill=(35,25,8,150))
sh=sh.filter(ImageFilter.GaussianBlur(7)); base=Image.alpha_composite(base,sh); d=ImageDraw.Draw(base)
for x,yy,txt,f,col,sw in pos:
    if sw>0: d.text((x,yy),txt,font=f,fill=col,stroke_width=sw,stroke_fill=(0,0,0,255))
    else:    d.text((x,yy),txt,font=f,fill=col)
print(f"CX={CX} bloco final x=[{minx},{maxx}]")
TCUT=N/FPS
for i in range(N):
    t=i/FPS
    p=min(max(t/SDUR,0),1); p=1-(1-p)**3          # ease-out cubico
    dx=int(-(1-p)*SLIDE)                          # desliza de -SLIDE -> 0 (sai de tras da cabeca)
    canvas=Image.new("RGBA",(W,H),(0,0,0,0)); canvas.paste(base,(dx,0),base)
    a=1.0
    if t<FIN: a=t/FIN
    if t>TCUT-FOUT: a=min(a,max(0.0,(TCUT-t)/FOUT))
    arr=np.array(canvas); arr[:,:,3]=(arr[:,:,3]*a).astype('uint8')
    Image.fromarray(arr,'RGBA').save(OUTDIR/f"t_{i+1:04d}.png")
print(f"OK -> {OUTDIR}/t_%04d.png  ({N} frames, TCUT={TCUT:.2f}s)")

# previews opcionais (só se os recortes ja existirem)
try:
    for fi in (12,50):
        bg=Image.open(EDIT/"behind"/"frames"/f"f_{fi:04d}.png").convert("RGBA")
        ti=Image.open(OUTDIR/f"t_{fi:04d}.png").convert("RGBA")
        fg=Image.open(EDIT/"behind"/"fg"/f"f_{fi:04d}.png").convert("RGBA")
        Image.alpha_composite(Image.alpha_composite(bg,ti),fg).convert("RGB").save(
            EDIT/"behind"/f"font_prev_{fi}.jpg",quality=92)
    print("previews ok")
except FileNotFoundError:
    print("(previews pulados: recortes ainda nao gerados)")
