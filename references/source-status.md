# Source Status / Citation Audit

**Audit date:** 2026-04-30  
**Scope:** URLs in `README.md`, `references/*.md`, `experiments/*.md`, and research prompts.

This file tracks citation hygiene separately from the research synthesis. A 403 from automated fetching is not automatically a bad source; it usually means anti-bot, login, or publisher restrictions. Items below are prioritized by whether they affect credibility or need manual verification.

## Summary

Automated URL extraction found **116 unique URLs** across the repo at audit time.

- Most anchor sources resolved or were extractable.
- Several publisher/hosted pages returned 403 to automated checks and need browser/manual verification.
- A few links should be fixed to canonical URLs.
- Some claims based on event recaps or secondary reporting need primary-source links before being treated as strong evidence.

## High-Confidence Anchor Sources

These were reachable/extractable and are safe to use as core anchors.

| Source | URL | Role in research | Confidence |
|---|---|---|---|
| Software 2.0 | https://karpathy.medium.com/software-2-0-a64152b37c35 | Weights-as-code framing | High, but Medium may 403 automated checks |
| Mirage / AmongAI | https://amongai.com/2025/12/10/hallucinate-any-app-one-screen-at-a-time/ | Closest weak-projection app demo | High |
| GameNGen | https://arxiv.org/abs/2408.14837 | Neural game runtime / world-model analogy | High |
| Genie 3 | https://deepmind.google/blog/genie-3-a-new-frontier-for-world-models/ | Interactive world-model SOTA analogy | High |
| A2UI | https://a2ui.org/ | Declarative agent UI contrast case | High |
| A2UI Google blog | https://developers.googleblog.com/introducing-a2ui-an-open-project-for-agent-driven-interfaces/ | Agent-driven UI protocol contrast | High |
| AG-UI | https://docs.ag-ui.com/introduction | Agent↔UI protocol contrast | High |
| MCP Apps | https://blog.modelcontextprotocol.io/posts/2026-01-26-mcp-apps/ | Tool-returned iframe UI contrast | High |
| Thesys C1 | https://docs.thesys.dev/guides/how-c1-works | Generative UI middleware contrast | High |
| Memori | https://arxiv.org/html/2603.19935 | Persistent memory / externalized state contrast | High |
| Computer-Using World Model | https://huggingface.co/papers/2602.17365 | UI-world-model analogy | Medium-high; HF page reachable |
| LiMAC | https://arxiv.org/html/2410.17883v1 | Hidden states projected to UI element space | High |
| Transformers are Multi-State RNNs | https://arxiv.org/abs/2401.06104 | Theoretical framing for transformer state/KV cache | High |

## Links To Fix / Prefer Canonical

| Current / issue | Replacement / action | Reason |
|---|---|---|
| `https://arxiv.gg/abs/2310.08560` | `https://arxiv.org/abs/2310.08560` | Use canonical arXiv for MemGPT |
| `https://papers.nips.cc/paper/8825` | `https://papers.nips.cc/paper_files/paper/2019/hash/c20a7ce2a627ba838cfbff082db35197-Abstract.html` | Short URL returned 404 in automated check |
| `https://support.claude.com/en/articles/11649438` | Replace with current Anthropic docs/support link or remove | Returned 404; claim about Artifacts persistence needs a current source |
| `PAGE` vs `PAGEN` naming | Use the source's actual dataset name after checking the paper/project page | Avoid propagating a model-generated typo |

## Manual Verification Needed

These sources may be valid but should not be used as critical evidence until manually opened in a browser or replaced with primary sources.

| Source | URL | Note |
|---|---|---|
| Karpathy AI Ascent / MenuGen recap | `https://app.dealroom.co/news/note/vibe-coding-was-just-the-warmup-andrej-karpathy-on-the-dawn-of-software-3-0` | Automated check got 403. Prefer a recording/transcript/primary post if available. |
| Claude Artifacts support page | `https://support.claude.com/en/articles/11649438` | 404. Needs replacement before citing. |
| ACM GenerativeGUI | `https://dl.acm.org/doi/10.1145/3706599.3719743` | 403 from automated check; likely publisher restriction. Verify manually. |
| OpenAI Sora world-simulator page | `https://openai.com/index/video-generation-models-as-world-simulators/` | 403 from automated check; verify manually. |
| Medium posts | Medium URLs | 403 from automated check is common; verify manually. |
| ScienceDirect NeuronautLLM | ScienceDirect URL in Opus artifact | 403 from automated check; verify manually and consider DOI/arXiv alternative. |
| Web World Models review | `https://liner.com/review/web-world-models` | Secondary review source; use cautiously or replace with original paper/post. |
| AMI Labs TechCrunch coverage | TechCrunch URL | Secondary reporting; use as company-direction evidence only, not technical proof. |

## Claims That Need Tighter Sourcing

| Claim | Current status | Suggested fix |
|---|---|---|
| “Karpathy's 2026 AI Ascent talk extended this to neural net internal state as application.” | Based on prompt/framing and secondary recap; not yet primary-sourced in repo. | Add transcript/video timestamp or weaken to “related framing around LLMs as kernel / MenuGen-style app obsolescence.” |
| “Mirage state machine is fully inside the model.” | Too strong. Mirage state is likely transcript/context-mediated, not hidden-state authoritative. | Phrase as “closest weak-projection demo: the model re-projects app state from interaction history.” |
| “GameNGen/Oasis/Genie prove the network can be runtime.” | Directionally fair for visual environment simulation; overextends to business apps. | Keep as analogy and explicitly list missing invariants/transactions/debuggability. |
| “Current models can maintain coherent state across much longer interactions.” | Broad and not directly sourced. | Cite benchmarks or remove from canonical docs. |
| “Two sessions independently converged.” | Prompts were nearly identical. | Phrase as “two model-assisted surveys using the same framing converged.” |

## Missing Coverage To Add Later

The current survey is strong enough for a first pass. For publication-quality work, add coverage of:

- **Model-based RL:** MuZero, DreamerV2/V3, PlaNet.
- **Differentiable memory:** Neural Turing Machines, Differentiable Neural Computers, Memory Networks.
- **Long-context/recurrent transformers:** Transformer-XL, Compressive Transformer, Memorizing Transformers, recurrent memory transformers.
- **State-space sequence models:** Mamba, RWKV, RetNet-style recurrent inference where relevant.
- **UI agent benchmarks:** OSWorld, WebArena, AndroidWorld, MiniWoB++, SeeAct, WebVoyager.
- **Mechanistic interpretability:** probing, sparse autoencoders, activation patching, causal tracing, representation editing.
- **Symbolic counter-thesis:** databases, CRDTs, event sourcing, type systems, formal methods, and why durable symbolic state remains dominant.

## Citation Policy For This Repo

1. Use canonical URLs where possible: arXiv, official docs, project pages, papers, GitHub repos.
2. Treat company marketing pages as directional evidence, not technical proof.
3. Mark secondary reporting as secondary.
4. Do not let future-looking or model-generated claims become canonical without a primary source.
5. Keep raw model research artifacts preserved, but make `consolidated-research.md` and this file the citation standard.
