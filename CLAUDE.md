# Repositório de vídeos — clínica facetoface (Passo Fundo)

Reels de marketing (harmonização facial) editados com o skill **video-use** + ffmpeg.

## Presets de edição

Estilos nomeados e reutilizáveis ficam em `.claude/skills/video-use/presets/`.

- **“padrão”** — acabamento completo do reel da clínica. Quando o usuário disser
  **“edita no padrão”**, **“o de sempre”** ou a palavra-chave **padrão**, siga
  [`.claude/skills/video-use/presets/padrao/PADRAO.md`](.claude/skills/video-use/presets/padrao/PADRAO.md)
  (fonte de verdade). Scripts: `build.py`, `retouch.py`, `make_title_anim.py` na mesma pasta.
  Edite só o bloco **PER-VIDEO** (fontes, tomada boa, hesitações, cortes, texto do gancho).

## Regras do repositório

- **Segredos**: a chave do ElevenLabs mora em `.claude/skills/video-use/.env` — está no
  `.gitignore` e **NUNCA** deve ser commitada.
- **Vídeos grandes**: `*.mov`/`*.mp4` e a pasta `edit/` são ignorados no branch de código.
  O master de entrega vai no branch **`entrega/reel-final`** (`git add -f`), separado.
- **Fidelidade clínica**: no before/after, a footage da **paciente nunca** é retocada nem
  alterada. Retoque/ajuste de rosto valem só para o **apresentador**.
- **Fontes** (via apt, o Google Fonts é bloqueado pelo proxy): `fonts-ebgaramond`,
  `fonts-montserrat`.
