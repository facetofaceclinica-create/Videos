# Preset **“padrão”** — reel da clínica (harmonização facial)

> Palavra-chave: **padrão**. Quando o usuário pedir “edita no **padrão**” / “o de sempre”,
> aplique este preset. É o acabamento do reel da Aria/Aline (before→after + CTA) e deve
> ser reproduzível em qualquer vídeo novo trocando só o material.

Este documento é a **fonte de verdade** do estilo. A implementação canônica está em
`build.py`, `retouch.py`, `make_title_anim.py` (mesma pasta). Valores resumidos em
`padrao.json`. Construído em cima do skill **video-use** (respeita suas 12 regras).

---

## O que o preset entrega (visão do resultado)

Reel vertical 9:16, ~50–55s, ritmo “snappy”:

1. **Gancho** — título elegante surgindo **de trás da cabeça** do apresentador
   (deslize esquerda→direita): duas linhas finas em Montserrat creme + **uma palavra
   dourada** em EB Garamond Italic. Efeito “texto atrás da pessoa”.
2. **Caso (before)** — apresentador narrando, pausas/hesitações cortadas, **legenda
   Montserrat branca contínua**, rosto **dele** sutilmente retocado.
3. **Transição moderna** (zoom-punch + flash suave) na **revelação** (before→after).
4. **Revelação (after)** — footage da paciente, **100% intacta** (fidelidade do antes/depois).
5. **Corte/zoom-punch** antes do **CTA** (“clica no link abaixo”).
6. Por cima de tudo: **grade “modo cinema” sutil**, **vinheta discreta**, **selo
   “Passo Fundo”** no topo-centro, **áudio normalizado a −14 LUFS**.

Sem efeitos sonoros (removidos a pedido). Pele **natural** — crítico para a clínica.

---

## Fluxo de trabalho num vídeo novo

> Tudo acontece na pasta de sessão `edit/` (efêmera). Aponte com
> `export VIDEO_EDIT_DIR=/caminho/para/edit`.

1. **Transcrever** cada fonte com Scribe (`helpers/transcribe.py` do video-use) →
   `edit/transcripts/<nome>.json`. **Nunca re-transcrever** fonte imutável (cache).
2. **Achar a tomada boa** de cada fonte (descartar falsos começos/bloopers): defina
   `tmin/tmax`, `drop` (hesitações tipo `"é,"`) e `cuts` (faixas a remover, ex.: frase
   repetida) no bloco **PER-VIDEO** de `build.py`.
3. **Preparar o gancho** (1x — ver §Gancho abaixo): extrair frames do seg00, rembg,
   recolorir com o retocado, rodar `make_title_anim.py` (editar o TEXTO do gancho).
4. **Rodar** `VIDEO_EDIT_DIR=… python3 build.py`. Ele: extrai segmentos → concat →
   retoca o apresentador → legenda ASS → composite (gancho+grade+selo+transições) →
   loudnorm → `edit/final_combined.mp4`.
5. **Entregar**: versão IG 2-pass ≤29,8 MiB via `SendUserFile`; master no branch
   `entrega/reel-final` (`git add -f`), fora do branch de código.

---

## Parâmetros do estilo (o “padrão”)

### Corte / ritmo
- `PAD_IN=0.05`, `PAD_OUT=0.14` (out maior: **deixa a palavra terminar** — Scribe marca o fim cedo).
- Separa segmentos em pausas **≥ 0.30s** (`GAP`). Corte sempre na **fronteira de palavra**.
- Fades de áudio de **30ms** em cada borda de segmento.
- Legenda em blocos de **≤3 palavras** (`CHUNK`).

### Cor / “modo cinema”
- **HDR HLG → SDR** via tonemap `hable` (string completa em `padrao.json` / `build.py`).
- `GRADE = eq(contrast 1.06, saturation 0.94, gamma 1.01)` +
  `colorbalance` (teal nas sombras `bs=0.028`, warm nos realces `rh=0.028`) +
  `curves` black-lift `0/0.012` e rolloff `1/0.988`.
- `VIG = vignette=angle=PI/4.7`.
- **Ordem dos filtros** no frame já composto: `GRADE → zoompan → flash → vignette`.

### Legenda (ASS, renderizada por ÚLTIMO)
- **Montserrat 64**, branco `&H00FFFFFF`, contorno preto **3**, sombra **1**.
- Alinhamento **2** (base-centro), `MarginV=360` (abaixo do tablet), `MarginL/R=96`.
- **Caixa normal** com capitalização de início de frase.
- **Contínua**: cada bloco segura até o próximo começar (sem flicker). Duração mín. 0.45s.
- Limpeza: tira `,;:` finais e o ponto final; troca `{}` por `()`.
- **O gancho (seg00) não usa legenda pequena** — usa o título elegante.

### Gancho (título atrás da pessoa) — §Gancho
Efeito **texto-atrás-do-apresentador** em 3 camadas: `fundo → título animado → recorte
RGBA da pessoa por cima`.
- **Recorte**: `rembg` modelo `u2net_human_seg` nos frames do seg00.
  **Importante**: recolorir o recorte com a versão **retocada** (pegar a cor de
  `base_retouched` e reusar o alpha do rembg), senão o rosto do gancho fica **sem** retoque.
- **Título** (`make_title_anim.py`): 2 linhas finas Montserrat Medium creme
  `(248,244,236)` + **palavra dourada** `(201,160,70)` EB Garamond Italic **212px**;
  sombra soft só na dourada. Auto-ajuste das finas até caber em 615px; contorno preto leve.
- **Animação**: o bloco **desliza no eixo X** de `-250 → 0` em **0.85s** (ease-out cúbico),
  com fade-in 0.30s / fade-out 0.40s, **86 frames @30fps** (~2.87s). Como a borda esquerda
  fica atrás do recorte, o texto **sai de trás da cabeça** e para inteiro visível
  (borda esq. final `x=430`, logo depois da cabeça).
- Overlay ativo só em `t < TCUT` (duração do seg00); no resto, legenda na frente normal.

### Transições (não-destrutivas — não mexem no timeline/áudio)
- **Zoom-punch** via `zoompan`, `z` = gaussiana no frame do evento, centralizado:
  revelação amp **0.10** (σ 3.2), CTA amp **0.085** (σ 3.0).
- **Flash** só na revelação: `eq=brightness` gaussiana em `t`, amp **0.12**, σ **0.055s**.
- Pontos: **revelação** = 1º segmento do 2º clipe (before→after); **CTA** = 1ª palavra do CTA
  (`CTA_START`, ex.: “**Se** você também quer…”).

### Retoque facial (SÓ o apresentador) — §Retoque
- `mediapipe FaceMesh` **0.10.14** (o stub “1.0.0” não tem `.solutions`). Pega o **rosto
  maior** (ignora rosto < 200px = foto no tablet).
- Máscara = **oval do rosto menos olhos/sobrancelhas/boca**, feather (GaussianBlur 9).
- Nível **“mais sutil”**: suavização `S=0.42` (bilateral 11/50/50 ×2), clareado de sombra
  `L=0.33`, `GAMMA=0.93` (levanta olheira / bigode chinês).
- **Aplica só nos frames do apresentador (< CUTOFF).** A **paciente** (2ª fonte) passa
  **100% intacta** — o antes/depois **nunca** é retocado. **Regra inegociável.**
- Cache por assinatura das faixas do apresentador (`base_retouched.sig`).

### Selo “Passo Fundo”
- `assets/passo_fundo.png` (RGBA, **transparência real**): pílula branca arredondada +
  pin roxo + “Passo Fundo” Montserrat SemiBold preto + sombra sutil.
- Composição: `scale=380:-1`, `overlay=(W-w)/2:85` (**topo-centro, y=85**). **Não tapa rostos.**

### Áudio
- `loudnorm` dois passes: **I=−14 LUFS, TP=−1 dBTP, LRA=11**, `linear=true` (mede, depois aplica).
- AAC 192k / 48kHz.

### Encode
- Segmento: `libx264 -preset medium -crf 17`. Composite: `-preset slow -crf 18`.
  `pix_fmt yuv420p`, `+faststart`. 60fps → conformado a **30fps**.

---

## Entrega / armazenamento
- **Master**: `edit/final_combined.mp4` (~52s, ~54MB). Vai só no branch **`entrega/reel-final`**
  (`git add -f`, pois `.gitignore` ignora `*.mp4`/`*.mov`/`edit/`). **Nunca** no branch de código.
- **Instagram** (SendUserFile tem teto de 30 MiB): 2-pass CBR ~4600k → ~29,8 MiB.
- Google Drive MCP (`create_file`) só aceita base64 inline → **inviável** para vídeo.

## Dependências
- **CLI**: `ffmpeg`, `ffprobe`.
- **pip**: `mediapipe==0.10.14`, `opencv-python`, `pillow`, `numpy`, `rembg`.
- **Fontes (apt)**: `fonts-ebgaramond`, `fonts-montserrat` (download do Google Fonts é
  bloqueado pelo proxy do GitHub — usar apt).
- **API**: ElevenLabs **Scribe** (chave em `.env`, **NUNCA** commitar — está no `.gitignore`).

## Armadilhas conhecidas (já resolvidas — não repetir)
- `.env` vazio “sombreia” a variável de ambiente → escrever a chave real.
- `-loop 1 -i img.png` **sem** `-t` trava o ffmpeg (input infinito) → usar sequência finita.
- Cache de segmento por **índice** quebra ao re-segmentar → cachear por **faixa**
  (`seg_<stem>_<ini>_<fim>.mp4`).
- Token arrastado do Scribe (ex.: “Eeee”) esconde pausa longa → subir `tmin` para pular.
- Recorte do gancho vindo do frame **original** deixa o rosto sem retoque → recolorir com
  `base_retouched` mantendo o alpha do rembg.
- Rodar build em background: usar o mecanismo de background do harness, **não** `&` no shell.
