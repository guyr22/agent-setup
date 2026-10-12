---
name: eng-ui
description: Change an existing application's UI using its design system and verify rendered interactions and relevant viewport states.
---

Inspect nearby components, tokens, layout patterns, accessibility conventions, and the requested interaction. Reuse the established design system. Do not install Figma or introduce a parallel framework for a local change.

Define relevant acceptance states, including loading/error/empty states only where affected. Implement the smallest coherent change while preserving unrelated state and API contracts.

Start the application and required services with the project's established commands, confirm readiness, and open it using available browser tools. Exercise affected user journeys against the intended test backend, including persistence or other downstream effects when relevant. Inspect representative sizes and affected controls, keyboard/focus behavior, and navigation. Run the project's critical smoke journeys and checks for neighboring behavior affected by shared components. Screenshots do not prove interaction correctness. Capture useful evidence and avoid tests that only mirror cosmetic implementation.

Fix defects introduced by the work and repeat failed interactions plus affected regression checks on the repaired version. Follow `eng-verify` for environment boundaries, repair routing, and evidence. If browser access or application startup is blocked, report the precise limitation and unverified journeys; a mocked preview only verifies the behavior it actually exercises. Separate verified behavior from visual inference. New design-system observations need a source; broader product choices remain explicit decisions.
