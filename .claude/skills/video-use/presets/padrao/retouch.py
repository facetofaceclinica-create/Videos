#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PRESET "padrão" — retoque facial SUTIL, SÓ do apresentador.
============================================================
Lê base_combined.mp4, detecta a malha do rosto MAIOR (o apresentador, não a foto no
tablet nem a paciente), suaviza a pele (bilateral, preservando olhos/sobrancelhas/boca)
e clareia levemente as sombras (olheira / bigode chinês). Aplica SÓ nos frames do
apresentador (< CUTOFF, passado pelo build). O restante — a footage da PACIENTE — passa
100% INTACTO (before/after fiel). Saída: base_retouched.mp4 (vídeo retocado + áudio original).

CRÍTICO: a paciente (segunda fonte / frames >= CUTOFF) NUNCA é retocada. Fidelidade do
antes/depois é inegociável para a clínica.

Uso (chamado pelo build.py):  VIDEO_EDIT_DIR=/caminho/edit  python3 retouch.py <CUTOFF_frames>
Requer: mediapipe==0.10.14 (o stub "1.0.0" não tem .solutions), opencv, numpy.
"""
import cv2, numpy as np, mediapipe as mp, subprocess, sys, os
from pathlib import Path

EDIT=Path(os.environ.get("VIDEO_EDIT_DIR","/home/user/Videos/edit"))
SRC=EDIT/"base_combined.mp4"; OUT=EDIT/"base_retouched.mp4"
CUTOFF=int(sys.argv[1]) if len(sys.argv)>1 else 794   # frames do apresentador (passado pelo build)

# ===== PRESET "padrão" — nível "mais sutil" (pedido do usuário) =====
S,L,GAMMA = 0.42, 0.33, 0.93      # S=mistura do suavizado | L=mistura do clareado | GAMMA<1 levanta sombra
MIN_FACE_PX = 200                 # rosto menor que isto (tablet) é ignorado
# ====================================================================

FM=mp.solutions.face_mesh
cap=cv2.VideoCapture(str(SRC))
W=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)); H=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
N=int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
print(f"base {W}x{H} {N} frames | retocando os primeiros {CUTOFF}")
fm=FM.FaceMesh(static_image_mode=False,max_num_faces=2,refine_landmarks=True,
               min_detection_confidence=0.4,min_tracking_confidence=0.4)
oval=sorted({i for e in FM.FACEMESH_FACE_OVAL for i in e})
excl=[sorted({i for e in g for i in e}) for g in
      (FM.FACEMESH_LEFT_EYE,FM.FACEMESH_RIGHT_EYE,FM.FACEMESH_LEFT_EYEBROW,
       FM.FACEMESH_RIGHT_EYEBROW,FM.FACEMESH_LIPS)]
proc=subprocess.Popen(
    ['ffmpeg','-y','-f','rawvideo','-pix_fmt','bgr24','-s',f'{W}x{H}','-r','30','-i','-',
     '-i',str(SRC),'-map','0:v','-map','1:a','-c:v','libx264','-preset','medium','-crf','16',
     '-pix_fmt','yuv420p','-c:a','copy','-movflags','+faststart',str(OUT)],
    stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def retouch(img):
    res=fm.process(cv2.cvtColor(img,cv2.COLOR_BGR2RGB))
    if not res.multi_face_landmarks: return img
    fl=max(res.multi_face_landmarks,
           key=lambda f:max(p.x for p in f.landmark)-min(p.x for p in f.landmark))
    pts=np.array([[p.x*W,p.y*H] for p in fl.landmark],np.float32)
    if pts[:,0].max()-pts[:,0].min() < MIN_FACE_PX: return img   # rosto pequeno (tablet) -> ignora
    mask=np.zeros((H,W),np.uint8)
    cv2.fillConvexPoly(mask,cv2.convexHull(pts[oval].astype(np.int32)),255)
    for idx in excl: cv2.fillConvexPoly(mask,cv2.convexHull(pts[idx].astype(np.int32)),0)
    mask=cv2.GaussianBlur(mask,(0,0),9)
    x0,y0=int(pts[:,0].min()),int(pts[:,1].min()); x1,y1=int(pts[:,0].max()),int(pts[:,1].max())
    pad=30; x0=max(0,x0-pad); y0=max(0,y0-pad); x1=min(W,x1+pad); y1=min(H,y1+pad)
    roi=img[y0:y1,x0:x1]; mroi=(mask[y0:y1,x0:x1]/255.0)[...,None]
    sm=cv2.bilateralFilter(roi,11,50,50); sm=cv2.bilateralFilter(sm,11,50,50)
    o=(roi*(1-mroi*S)+sm*(mroi*S)).astype(np.uint8)
    lift=(255*np.power(o/255.0,GAMMA)).astype(np.uint8)
    o=(o*(1-mroi*L)+lift*(mroi*L)).astype(np.uint8)
    out=img.copy(); out[y0:y1,x0:x1]=o
    return out

i=0
while True:
    ok,frame=cap.read()
    if not ok: break
    if i<CUTOFF: frame=retouch(frame)      # < CUTOFF = apresentador; >= CUTOFF = paciente (intacta)
    proc.stdin.write(frame.tobytes())
    if i%150==0: print(f"  {i}/{N}", flush=True)
    i+=1
cap.release(); proc.stdin.close(); proc.wait()
print(f"OK -> {OUT}  ({i} frames)")
