---
name: eng-ui
description: Change an existing application's UI using its design system and verify rendered interactions and relevant viewport states.
---

Inspect nearby components, tokens, layout patterns, accessibility conventions, and the requested interaction. Reuse the established design system. Do not install Figma or introduce a parallel framework for a local change.

Define relevant acceptance states, including loading/error/empty states only where affected. Implement the smallest coherent change while preserving unrelated state and API contracts.

Use native browser tools and the established preview command when available. Inspect representative sizes and exercise affected controls, keyboard/focus behavior, and navigation. Screenshots do not prove interaction correctness. Capture useful evidence and avoid tests that only mirror cosmetic implementation.

Run appropriate local checks and explain preview limitations. Separate verified behavior from visual inference. New design-system observations need a source; broader product choices remain explicit decisions.
