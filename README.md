# Ask Giorgio

Ask Giorgio is an experimental, open-source conversational museum companion designed around one principle:

> Look at the art. Not the phone.

It runs inside a compatible AI service supplied by the visitor. Ask Giorgio provides the guiding protocol; the visitor's AI account provides the model, voice interface, and usage.

## Current status

This repository contains an **experimental draft** for desk testing. It has not yet passed the planned evidence-mode tests and must not be presented as a verified museum guide. Its central trust rule is:

> Never imply that Ask Giorgio sees, knows, or has verified a work-specific visual detail without evidence for that exact work.

## Contents

- `ask-giorgio/SKILL.md` — portable Agent Skills entry point.
- `ask-giorgio/references/protocol.md` — complete Ask Giorgio museum-guide protocol.
- `ask-giorgio/references/visitor-profile-template.md` — optional visitor-owned continuity file.

No Museum Packs are included in this initial repository.

## Website and downloads

Visit **[AskGiorgio.com](https://askgiorgio.com/)** to choose your visit style and copy the complete experimental guide into your own AI conversation. The website remains **work in progress** and unannounced, with search indexing discouraged by page metadata and response headers (not access controls).

The visit-style, time, museum, and interest controls prepare preferences; the website does not generate routes or save/send your inputs. **Copy the guide** includes your chosen settings. Downloads are generic and do not contain those settings:

- [Universal package](https://askgiorgio.com/downloads/ask-giorgio-universal-v0.1.1.zip) — readable protocol, instructions, optional visitor-profile template, and licenses.
- [Agent Skill package](https://askgiorgio.com/downloads/ask-giorgio-skill-v0.1.1.zip) — `ask-giorgio/` with `SKILL.md`, referenced files, and licenses, for compatible hosts.
- [Blank visitor-profile template](https://askgiorgio.com/downloads/ask-giorgio-profile.md) — optional file you review and carry yourself, not automatic memory.
- [Download checksums](https://askgiorgio.com/downloads/manifest.json).

Distribution **v0.1.1** publishes the website and licensed packages; the experimental guide/skill content remains **v0.1.0**, unchanged. The previous GitHub release is preserved. No Museum Packs are included.

Vercel serves only `site/`, as configured in `vercel.json`. No build dependencies, AI API, database, visitor accounts, or analytics are used. Image/font provenance and licenses are available on the website's credits page. Updating the website does not require changing DNS again.

## Build and verify

The repository is self-contained: `website/` holds the HTML/JavaScript sources, `scripts/build.py` generates `site/index.html`, `site/guide.js`, credits, and reproducible ZIPs from the public protocol and licenses. Licensed images/fonts remain in `site/assets/`.

```sh
python3 scripts/build.py
python3 -m unittest discover -s tests -p 'test_*.py'
python3 -m pip install -r tests/requirements.txt
python3 -m playwright install chromium
python3 tests/verify_site.py --channel chromium
```

The browser test starts a temporary local server, checks interactive setup/clipboard/downloads and responsive layouts, and writes ignored reports to `test-results/`. It also accepts a public URL for post-deployment verification. Browser tests do not establish museum-guide accuracy or validate third-party onboarding. The planned evidence-mode desk tests remain outstanding.

Deployment is manual using the existing Vercel project; GitHub auto-deploy is not connected. Never publish `.env*`, `.vercel/`, local test output, or internal project notes.

## Use

On a service that supports Agent Skills, install or upload the `ask-giorgio` folder in the manner documented by that service. Otherwise, use `ask-giorgio/references/protocol.md` as the setup prompt in a new AI conversation.

Provider support and installation steps vary. Review the package before installing it, and verify current instructions with the provider.

## Licensing

- Code and packaging scripts, if added, are licensed under the [MIT License](LICENSE).
- Original prompts, skill instructions, documentation, and original Museum Pack text are licensed under [Creative Commons Attribution 4.0 International](LICENSE-CONTENT.txt).
- Third-party text, images, collection data, trademarks, and other materials are not relicensed. Their original terms continue to apply.

Suggested attribution: **Ask Giorgio by Dan Rudy — AskGiorgio.com**.

Ask Giorgio is not affiliated with or endorsed by any museum, OpenAI, Anthropic, or other AI provider.
