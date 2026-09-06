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

## Use

On a service that supports Agent Skills, install or upload the `ask-giorgio` folder in the manner documented by that service. Otherwise, use `ask-giorgio/references/protocol.md` as the setup prompt in a new AI conversation.

Provider support and installation steps vary. Review the package before installing it, and verify current instructions with the provider.

## Licensing

- Code and packaging scripts, if added, are licensed under the [MIT License](LICENSE).
- Original prompts, skill instructions, documentation, and original Museum Pack text are licensed under [Creative Commons Attribution 4.0 International](LICENSE-CONTENT.txt).
- Third-party text, images, collection data, trademarks, and other materials are not relicensed. Their original terms continue to apply.

Suggested attribution: **Ask Giorgio by Dan Rudy — AskGiorgio.com**.

Ask Giorgio is not affiliated with or endorsed by any museum, OpenAI, Anthropic, or other AI provider.
