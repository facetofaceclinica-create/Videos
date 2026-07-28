# Videos — edição de vídeo com IA (video-use)

Este repositório está configurado com a ferramenta open-source
**[video-use](https://github.com/browser-use/video-use)** (licença MIT), que
permite **editar vídeos conversando com o Claude Code** — sem editor tradicional,
sem menus.

Você solta o material bruto numa pasta, abre uma sessão do Claude Code aqui e diz
algo como *"edite isso num vídeo de lançamento"*. O Claude transcreve, corta
vícios de fala e silêncios, faz correção de cor, queima legendas, gera animações
e entrega um `edit/final.mp4`.

## Estrutura

```
.
├── .claude/
│   └── skills/
│       └── video-use/        ← a skill (detectada automaticamente pelo Claude Code)
│           ├── SKILL.md       ← regras de edição e uso diário
│           ├── install.md     ← passos de instalação
│           ├── helpers/        ← scripts de edição (transcribe, render, grade, timeline_view…)
│           └── skills/manim-video/  ← skill de animação (opcional)
├── .gitignore
└── README.md
```

As **saídas** de cada sessão ficam em `edit/` ao lado do seu material
(ex.: `edit/final.mp4`) e **não** são versionadas por padrão.

## Como usar

1. **Solte o material bruto** neste diretório (arquivos `.mp4`, `.mov` etc.),
   ou peça ao Claude para baixar de uma URL (usa `yt-dlp`).
2. **Abra uma sessão** do Claude Code neste repositório.
3. **Peça a edição**, por exemplo:
   - *"faça um inventário desses takes e proponha uma estratégia"*
   - *"edite isso num vídeo de lançamento com legendas"*

O Claude sempre **propõe um plano e espera sua confirmação** antes de cortar.

## Chave da ElevenLabs (transcrição)

A transcrição usa a API **ElevenLabs Scribe** — é necessária uma chave.
Configure de forma segura, **sem colar a chave no chat**:

- **No Claude Code na web (recomendado):** adicione a variável de ambiente
  `ELEVENLABS_API_KEY` nas configurações do seu ambiente. Assim ela é injetada
  automaticamente em toda sessão e nunca vai para o Git.
  Veja: <https://code.claude.com/docs/en/claude-code-on-the-web>
- **Em uso local:** copie `.claude/skills/video-use/.env.example` para
  `.claude/skills/video-use/.env` e coloque a chave lá (esse arquivo é ignorado
  pelo Git).

Pegue/gere sua chave em <https://elevenlabs.io/app/settings/api-keys>.

## Observações sobre o ambiente na web

O ambiente do Claude Code na web é **efêmero** — o container é recriado após um
tempo de inatividade. Isso significa que `ffmpeg` e as dependências Python podem
precisar ser **reinstalados a cada nova sessão**. Os arquivos deste repositório
(a skill) persistem porque estão versionados no Git; o que se perde é o software
instalado no sistema. Se quiser que a instalação seja automática a cada sessão,
peça ao Claude para criar um **hook de SessionStart**.

Para instalar manualmente numa nova sessão:

```bash
apt-get update && apt-get install -y ffmpeg          # ffmpeg (obrigatório)
uv pip install --system requests librosa matplotlib pillow numpy
```

---

Ferramenta original: <https://github.com/browser-use/video-use> · Licença MIT.
