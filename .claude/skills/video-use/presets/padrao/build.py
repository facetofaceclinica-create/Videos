#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PRESET "padrão" — pipeline de montagem para reels da clínica (harmonização facial).
=====================================================================================
Este é o motor que produziu o reel da Aline. Reproduz o MESMO acabamento em qualquer
vídeo novo: cortar pausas/hesitações, legenda Montserrat contínua, gancho com título
dourado surgindo de trás da cabeça, transições zoom-punch, grade "modo cinema" sutil,
retoque facial só do apresentador (paciente 100% intacta), selo "Passo Fundo" no topo,
áudio a −14 LUFS.

COMO USAR NUM VÍDEO NOVO
------------------------
1. Coloque as fontes .MOV e transcreva com Scribe (helpers/transcribe.py do video-use).
   NÃO re-transcrever fontes já cacheadas.
2. Prepare o gancho (título + recorte da pessoa) rodando make_title_anim.py e o rembg
   (veja PADRAO.md §Gancho). Isso gera edit/behind/title_anim/ e edit/behind/fg/.
3. Edite APENAS o bloco  ▼ PER-VIDEO ▼  abaixo (fontes, tomada boa, hesitações, cortes).
   Todo o resto é o PRESET — não mexer para manter o padrão.
4. Rode:  VIDEO_EDIT_DIR=/caminho/para/edit  python3 build.py
5. Entregue: final_combined.mp4 (master) + versão IG 2-pass ≤29,8 MiB (SendUserFile).
   Master grande vai só no branch de entrega (entrega/reel-final), nunca no branch de código.

Regras do skill video-use respeitadas: extract por-segmento -> concat -c copy -> legenda
POR ÚLTIMO -> loudnorm; cortes na fronteira de palavra; padding; ASR por palavra; cache.

Dependências: ffmpeg, mediapipe==0.10.14, opencv, pillow, numpy, rembg[u2net_human_seg].
Fontes (apt): fonts-ebgaramond, fonts-montserrat.  Chave Scribe em .env (NUNCA commitar).
"""
import json, subprocess, sys, os
from pathlib import Path

# Pasta de trabalho da sessão (efêmera). Sobrescreva com VIDEO_EDIT_DIR no vídeo novo.
EDIT = Path(os.environ.get("VIDEO_EDIT_DIR", "/home/user/Videos/edit"))
HERE = Path(__file__).resolve().parent          # pasta do preset (onde vivem retouch.py e assets/)

# ================= PRESET "padrão" — NÃO ALTERAR (é a identidade visual) =================
PAD_IN, PAD_OUT = 0.05, 0.14      # padding do corte; PAD_OUT maior deixa a palavra TERMINAR
GAP, CHUNK = 0.30, 3              # separa segmentos em pausas >=0.30s; <=3 palavras por legenda
TONEMAP = ("zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,"
           "tonemap=tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p")  # HDR HLG -> SDR
W, H, FPS = 1080, 1920, 30
BADGE = HERE/"assets"/"passo_fundo.png"           # selo Passo Fundo (transparência real)
BADGE_W, BADGE_Y = 380, 85                        # escala e Y do selo (topo-centro, não tapa rostos)
# Grade cinema sutil (pele natural — CRÍTICO p/ clínica):
GRADE = ("eq=contrast=1.06:saturation=0.94:gamma=1.01,"
         "colorbalance=rs=-0.02:bs=0.028:rm=0.012:bm=-0.006:rh=0.028:bh=-0.024,"
         "curves=master='0/0.012 0.5/0.5 1/0.988'")
VIG = "vignette=angle=PI/4.7"
# ========================================================================================

# ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼ PER-VIDEO — EDITE SÓ ISTO A CADA VÍDEO ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼
#  src   = arquivo fonte (.MOV)             tr   = transcrição Scribe cacheada (JSON)
#  tmin/tmax = janela da TOMADA BOA (s)     drop = tokens de hesitação a remover ("é," etc.)
#  cuts  = faixas [ (ini,fim) ] a remover DENTRO da tomada (ex.: frase repetida)
CLIPS = [
    {"src": Path("/home/user/Videos/IMG_7520.MOV"), "tr": EDIT/"transcripts"/"IMG_7520.json",
     "tmin": 15.0, "tmax": 1e9, "drop": {"é,"}, "cuts": [(37.95, 39.01)]},  # remove "pra que trouxesse,"
    {"src": Path("/home/user/Videos/IMG_7521.MOV"), "tr": EDIT/"transcripts"/"IMG_7521.json",
     "tmin": 36.0, "tmax": 1e9, "drop": set()},   # 36.0 pula o "Eeee" arrastado (34.62-35.96)
]
# Palavra que começa o CTA (define o 2º ponto de transição). Ex.: "Se você também quer..."
CTA_START = "se"
# ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲ FIM PER-VIDEO ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲

def ff(a): subprocess.run(a, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
def pdur(p): return float(subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
    "-of","default=nk=1:nw=1",str(p)], capture_output=True, text=True).stdout.strip())
def pdim(p):
    o=subprocess.run(["ffprobe","-v","error","-select_streams","v:0","-show_entries","stream=width,height",
        "-of","csv=p=0",str(p)], capture_output=True, text=True).stdout.strip()
    return tuple(map(int, o.split(",")))

# ---------------- 1) ranges de cada clipe ----------------
R=[]
for ci,c in enumerate(CLIPS):
    tr=json.load(open(c["tr"]))
    words=[w for w in tr["words"] if w.get("type")=="word" and w.get("start") is not None
           and c["tmin"]<=w["start"]<=c["tmax"]]
    cuts=c.get("cuts",[])
    kept=[w for w in words if w["text"].strip() not in c["drop"]
          and not any(a<=w["start"]<b for a,b in cuts)]
    segs,cur=[],[kept[0]]
    for a,b in zip(kept,kept[1:]):
        if b["start"]-a["end"]>=GAP: segs.append(cur); cur=[b]
        else: cur.append(b)
    segs.append(cur)
    for s in segs:
        R.append({"src":c["src"],"clip":ci,"start":max(0.0,round(s[0]["start"]-PAD_IN,3)),
                  "end":round(s[-1]["end"]+PAD_OUT,3),"words":s})

print(f"== {len(R)} segmentos (v1+v2) ==")
for i,r in enumerate(R):
    print(f"  seg{i:02d} [v{r['clip']+1}] {r['start']:6.2f}-{r['end']:6.2f}  \"{' '.join(w['text'] for w in r['words'])[:50]}\"")

# ---------------- 2) extrair ----------------
clips=EDIT/"clips_combined"
clips.mkdir(parents=True, exist_ok=True)
paths=[]
for i,r in enumerate(R):
    dur=round(r["end"]-r["start"],3)
    out=clips/f"seg_{r['src'].stem}_{r['start']:.2f}_{r['end']:.2f}.mp4"  # cache por FAIXA (robusto a re-segmentacao)
    fo=max(0.0,dur-0.03)
    if not out.exists():                       # reaproveita segmento so se a faixa for identica
        ff(["ffmpeg","-y","-ss",f"{r['start']:.3f}","-i",str(r['src']),"-t",f"{dur:.3f}",
            "-vf",f"{TONEMAP},scale={W}:{H}",
            "-af",f"afade=t=in:st=0:d=0.03,afade=t=out:st={fo:.3f}:d=0.03",
            "-r",str(FPS),"-c:v","libx264","-preset","medium","-crf","17","-pix_fmt","yuv420p",
            "-c:a","aac","-b:a","192k","-ar","48000","-movflags","+faststart",str(out)])
    d=pdur(out); w,h=pdim(out)
    if (w,h)!=(W,H): sys.exit(f"orient seg{i}: {w}x{h}")
    r["real"]=d; paths.append(out); print(f"  ok seg{i:02d}: {d:5.2f}s")

off=0.0
for r in R: r["offset"]=off; off+=r["real"]
TOTAL=off; print(f"== total combinado: {TOTAL:.2f}s ==")

# ---------------- 3) concat ----------------
cl=EDIT/"_concat.txt"; cl.write_text("".join(f"file '{p.resolve()}'\n" for p in paths))
base=EDIT/"base_combined.mp4"
ff(["ffmpeg","-y","-f","concat","-safe","0","-i",str(cl),"-c","copy","-movflags","+faststart",str(base)])
cl.unlink()
# retoque facial no v1 (apresentador) — paciente (v2) NUNCA é tocada.
# cache por assinatura das faixas de v1 (nao re-roda se v1 nao mudou)
v1sig="|".join(f"{r['start']:.2f}-{r['end']:.2f}" for r in R if r["clip"]==0)
brf=EDIT/"base_retouched.mp4"; sigf=EDIT/"base_retouched.sig"
if brf.exists() and sigf.exists() and sigf.read_text().strip()==v1sig:
    print("== base RETOCADA reaproveitada (v1 inalterado) ==")
else:
    v1n=round(next(r["offset"] for r in R if r["clip"]==1)*FPS)   # nº de frames do apresentador (v1)
    subprocess.run(["python3",str(HERE/"retouch.py"),str(v1n)],check=True,
                   env={**os.environ,"VIDEO_EDIT_DIR":str(EDIT)})
    sigf.write_text(v1sig); print(f"== base RETOCADA gerada (v1={v1n} frames) ==")
base=brf

# ---------------- 4) legenda ASS (caixa normal, continua) ----------------
def ot(w,r): return (w["start"]-r["start"])+r["offset"],(w["end"]-r["start"])+r["offset"]
SENT=(".","!","?"); cues=[]
for r in R:
    if r is R[0]: continue          # gancho usa o TITULO elegante (nao a legenda pequena)
    ch=[]
    for w in r["words"]:
        ch.append(w)
        if len(ch)>=CHUNK or w["text"].strip().endswith(SENT): cues.append((ch,r)); ch=[]
    if ch: cues.append((ch,r))
def ats(t):
    cs=int(round(max(0,t)*100)); h,cs=divmod(cs,360000); m,cs=divmod(cs,6000); s,cs=divmod(cs,100)
    return f"{h:d}:{m:02d}:{s:02d}.{cs:02d}"
def clean(ch):
    t=" ".join(w["text"].strip() for w in ch).strip().rstrip(",;:")
    if t.endswith("."): t=t[:-1]
    return t.replace("{","(").replace("}",")")
dlg=[]; prev_sent=True
for ch,r in cues:
    st,_=ot(ch[0],r); _,en=ot(ch[-1],r); txt=clean(ch)
    if prev_sent and txt[:1].islower(): txt=txt[0].upper()+txt[1:]   # capitaliza inicio de frase
    dlg.append([max(0,st),max(st+0.45,en),txt])
    prev_sent=ch[-1]["text"].strip().endswith((".","!","?"))
dlg.sort()
for i in range(len(dlg)-1): dlg[i][1]=dlg[i+1][0]   # legenda CONTINUA (segura ate a proxima)
dlg[-1][1]=max(dlg[-1][1],TOTAL-0.02)
ASS=("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nWrapStyle: 0\n"
     "ScaledBorderAndShadow: yes\n\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, "
     "SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, "
     "Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
     "Style: Def,Montserrat,64,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,3,1,2,96,96,360,1\n\n"
     "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
lines=[ASS]+[f"Dialogue: 0,{ats(st)},{ats(en)},Def,,0,0,0,,{txt}" for st,en,txt in dlg]
ass_path=EDIT/"subs_combined.ass"; ass_path.write_text("\n".join(lines))
print(f"== legenda: {len(dlg)} blocos ==")

# ---------------- 5) composite: gancho (texto ATRAS da pessoa) + legenda + grade + selo ----------------
# Camadas no gancho (seg00): fundo -> TITULO animado -> pessoa recortada por cima => texto surge
# de tras da cabeca (esq->dir). Legenda ASS por ultimo (so do seg01+), na frente normal.
TCUT=R[0]["real"]                                   # duracao do gancho (seg00)
title_seq=EDIT/"behind"/"title_anim"/"t_%04d.png"  # titulo ANIMADO (deslize esq->dir)
fg_seq=EDIT/"behind"/"fg"/"f_%04d.png"             # recortes RGBA da pessoa (cor RETOCADA + alpha rembg)
# Transicoes modernas (zoom-punch, nao-destrutivas): na REVELACAO (v1->v2) e antes do CTA.
# Flash suave so na revelacao. Aplicadas por ULTIMO, sobre o frame ja composto.
T1=next(r["offset"] for r in R if r["clip"]==1)     # inicio revelacao (1º seg de v2)
T2=next(r["offset"] for r in R if r["clip"]==1
        and r["words"][0]["text"].strip().lower().startswith(CTA_START))  # inicio CTA
f1=round(T1*FPS); f2=round(T2*FPS)
print(f"== transicoes: revelacao t={T1:.2f}s (frame {f1}) | CTA t={T2:.2f}s (frame {f2}) ==")
ZP=(f"zoompan=z='1+0.10*exp(-((in-{f1})/3.2)^2)+0.085*exp(-((in-{f2})/3.0)^2)'"
    f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={W}x{H}:fps={FPS}")
FLASH=f"eq=brightness='0.12*exp(-((t-{T1:.3f})/0.055)^2)':eval=frame"
inputs=["-i",str(base),"-framerate",str(FPS),"-i",str(title_seq),
        "-framerate",str(FPS),"-i",str(fg_seq),"-i",str(BADGE)]
fc=[f"[0:v][1:v]overlay=eof_action=pass:enable='lt(t,{TCUT:.3f})'[bt]",
    f"[bt][2:v]overlay=eof_action=pass:enable='lt(t,{TCUT:.3f})'[p]",
    f"[p]ass={ass_path}[vc]",
    f"[vc]{GRADE},{ZP},{FLASH},{VIG}[vg]",
    f"[3:v]scale={BADGE_W}:-1[badge]",
    f"[vg][badge]overlay=(W-w)/2:{BADGE_Y}[v]"]
aud="0:a"                                           # sem SFX: audio original do base direto
comp=EDIT/"composited_combined.mp4"
ff(["ffmpeg","-y",*inputs,"-filter_complex",";".join(fc),"-map","[v]","-map",aud,
    "-c:v","libx264","-preset","slow","-crf","18","-pix_fmt","yuv420p",
    "-c:a","aac","-b:a","192k","-ar","48000","-movflags","+faststart",str(comp)])
print("== composite ok ==")

# ---------------- 6) loudnorm (-14 LUFS, dois passes) ----------------
def loudnorm(src,dst):
    p=subprocess.run(["ffmpeg","-y","-hide_banner","-nostats","-i",str(src),
        "-af","loudnorm=I=-14:TP=-1:LRA=11:print_format=json","-vn","-f","null","-"],
        capture_output=True,text=True)
    e=p.stderr; a=e.rfind("{"); b=e.rfind("}"); data=None
    try: data=json.loads(e[a:b+1])
    except Exception: pass
    if data and {"input_i","input_tp","input_lra","input_thresh","target_offset"}<=set(data):
        flt=(f"loudnorm=I=-14:TP=-1:LRA=11:measured_I={data['input_i']}:measured_TP={data['input_tp']}"
             f":measured_LRA={data['input_lra']}:measured_thresh={data['input_thresh']}"
             f":offset={data['target_offset']}:linear=true")
        print(f"   loudnorm medido: I={data['input_i']} TP={data['input_tp']} LRA={data['input_lra']}")
    else: flt="loudnorm=I=-14:TP=-1:LRA=11"; print("   loudnorm fallback")
    ff(["ffmpeg","-y","-hide_banner","-nostats","-i",str(src),"-c:v","copy","-af",flt,
        "-c:a","aac","-b:a","192k","-ar","48000","-movflags","+faststart",str(dst)])
final=EDIT/"final_combined.mp4"; loudnorm(comp,final)
w,h=pdim(final); d=pdur(final); mb=final.stat().st_size/1e6
print(f"\n*** FINAL COMBINADO: {final}  {w}x{h}  {d:.2f}s  {mb:.1f} MB ***")
