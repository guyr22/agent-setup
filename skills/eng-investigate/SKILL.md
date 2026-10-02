---
name: eng-investigate
description: Investigate a reproducible bug, unexplained failure, or performance regression by testing hypotheses and identifying the causal path.
---

Establish expected behavior from the request and authoritative sources, then reproduce the failure or identify the missing evidence. Read the narrow call/data path and relevant changes. Separate observations from hypotheses.

Choose a check that discriminates between competing explanations. Prefer cheap local evidence before broad tracing. After two attempts that add no evidence, change the hypothesis or report the missing dependency. Do not store secrets or unrelated user data from logs.

Repair the supported cause within scope. Add a regression test when it demonstrates the failure mode, and check adjacent behavior that shares the cause. Report the causal explanation and actual verification; a plausible story without reproduction remains uncertain. Retain reusable project facts only with source evidence, without turning a single incident into global policy.
