# Research Consolidation — Neural App Runtime / Projection-Based Applications

**Compiled:** 2026-04-30  
**Purpose:** Merge insights from two model-assisted research sessions into a single canonical reference while preserving the individual artifacts.

**Audit note:** The two research sessions used nearly identical prompts. Their convergence is useful triangulation, but not independent empirical corroboration.

---

## 0. The Definition

A **strong projection-based application** satisfies:

1. The model's hidden/neural state (weights, activations, recurrent state, KV cache, or another latent state) is the authoritative holder of the app's state machine, domain logic, and data.
2. The visible UI is a rendering of that state, computed each tick by the model or a thin display/projection function. The UI is a view, not the program.
3. There is no durable symbolic application layer between user input and model state. If JSON, databases, files, tool calls, HTML handlers, or event buses hold canonical state or logic, the system is hybrid rather than strong projection.

Under this strict reading, **no mature system exists today**. The research from both sessions converges on this conclusion.

### Taxonomy

| Category | Canonical state lives in | Status |
|---|---|---|
| **Strong projection** | Model internals: activations, recurrent state, KV cache, latents, weights | Research target; no mature public system found |
| **Weak projection** | Prompt-visible transcript/context | Closest demos: Mirage/Websim-style hallucinated apps |
| **Hybrid projection** | JSON/db/files/event logs plus model mutation/rendering | Practical baseline, but not proof of the thesis |
| **Generative UI / agent UI** | UI specs, HTML, component trees, event protocols | Rendering/transport layer, not app identity |
| **World-model runtime** | Learned visual/environment dynamics | Strong analogy; lacks business/app semantics |
| **Codegen app** | Generated conventional source code | Opposite of projection; model exits runtime |

---

## 1. Closest Existing Artifacts

### Mirage / Among AI (Dec 2025) — Closest Weak-Projection Demo

- **Source:** https://amongai.com/2025/12/10/hallucinate-any-app-one-screen-at-a-time/
- **What it does:** User describes an app. Claude Haiku 4.5 emits HTML for the initial screen. Each interaction is sent back; the model emits the next HTML view "showing the new state." To-do list, Linux terminal, LISP interpreter, Win95 file manager.
- **Author's quote:** *"Besides the HTML… there is no code that ever gets generated. All the behaviors and functionalities of your app are made up by the LLM as you use it."*
- **Why it matters:** Mirage is the most literal public demo of a model-mediated app loop with no app-specific source code. The model re-projects the next UI from the prompt, transcript, and interaction history.
- **Important correction:** Mirage should not be treated as proof that hidden model state is the application. Its state is best understood as transcript/context-mediated unless the runtime exposes and uses model internals directly.
- **Gaps:**
  - No persistence outside context. When context fills, state vanishes.
  - Each interaction is a full LLM round-trip (~seconds per click).
  - State drifts mid-session because the model re-derives "what the app is" each turn.
  - HTML still renders client-side, so technically a browser-executes-JS layer exists.
- **Author's framing:** A toy. It proves the weak-projection pattern is possible, not that strong projection is solved.

### GameNGen / Oasis / Genie 3 — Visual Analogs

| System | What it proves | Gap |
|---|---|---|
| **GameNGen** (Google, 2024) | A diffusion model IS the DOOM runtime. Pixels are projections of hidden state. No DOOM source code in the loop. | Video frame predictor, not a business app. Drifts after minutes. |
| **Oasis 2.0** (Decart, 2025) | Real-time Minecraft-like world, engine-free, 20fps autoregressive. | Same. No semantic UI, no persistent business logic. |
| **Genie 3** (DeepMind, 2025) | Text-prompted interactive 3D worlds, ~1 min memory, promptable world events. | Demo-ware. No users, accounts, files, or domain logic. |

**Audit framing:** These systems strongly support the analogy that networks can act as runtimes for interactive visual environments. The leap from neural DOOM/Minecraft-like worlds to a CRM still requires solving business invariants, transactions, persistence, authorization, and debugging — no published technique found solves that inside hidden state.

### Websim.ai (2025)

- **Source:** https://websim.com/
- **What it does:** Type a fictitious URL → get an interactive hallucinated website. Clicks generate the next page via Claude 3.5 Sonnet.
- **Relation to projection:** Closer to Mirage. The "app" exists only in the model's interpretation of the URL plus interaction history.
- **Gap:** Each page is largely independent — more "creative writing rendered as web pages" than a stateful application.

---

## 2. What It Is NOT (The Engineering Counter-Thesis)

**Audit framing:** Two model-assisted surveys using the same definition identified these as the dominant adjacent paradigms — and as the **opposite** of strong projection-based apps:

| Category | Examples | Why it's not projection |
|---|---|---|
| **Generative UI** | Google Gemini, CopilotKit, CopilotKit generative-ui repo | Model generates HTML. Each interaction is roughly self-contained. HTML is the output, not a projection. |
| **Agent↔UI Protocols** | A2UI, AG-UI, MCP UI, Thesys C1 | Model emits structured UI data/specs. Deterministic client code renders it. Model is a generator, not a runtime. |
| **Projection/state protocols** | SLOP | Explicit semantic state tree plus contextual affordances. Strong substrate for weak/hybrid projection, but state is externalized unless backed by model internals. |
| **AI App Builders** | Lovable, Bolt, v0, Replit, Cursor | Model writes conventional code. The generated code IS the app. The model is gone at runtime. |
| **Agent Memory Systems** | Letta, MemGPT, Cloudflare Agent Memory | Model is a CPU that reads/writes to external memory. Not trusted to hold state. |
| **LLM-as-OS** | AIOS, AgentOS, Qualixar OS, Karpathy's "LLM kernel" | Model is a scheduler/orchestrator over external systems. Applications still live below it. |
| **Vibe Coding** | Karpathy's original framing | Prompt → code → app. Still a code layer. |

**Critical insight from the Opus session:** These protocols are built on the assumption that "the agent thinks and code renders." They are the engineering counter-thesis to projection. A projection-based runtime would treat all of these as scaffolding to be removed once models are reliable enough.

---

## 3. Academic Lineage

The strongest academic ancestors are **latent world models** and **neural program induction**, not frontend generation systems.

### Core Papers

| Paper | Year | What it establishes | Gap to projection |
|---|---|---|---|
| **Software 2.0** (Karpathy) | 2017 | Weights ARE code. Training IS compilation. | About classifiers, not stateful apps. |
| **LaSynth** (Chen et al.) | 2021 | A neural net holds an executable program in latent space and rolls it forward. | Targets small DSLs, produces program output artifacts. |
| **World Models** (Ha & Schmidhuber) | 2018 | Agent trains entirely inside a learned model. World IS the network. | RL environments, not user-facing apps. |
| **Transformers are Multi-State RNNs** (Oren et al.) | 2024 | Decoder transformers = multi-state RNNs with infinite multi-state size. | Theoretical license for "KV cache as RAM." |
| **JEPA / LeWorldModel** (LeCun) | 2022-2025 | Predictive architectures over learned latents. | Vision/language, no app-layer concepts. |
| **Decodable Neural Networks** | 2021 | Jointly trains nets so activations decode back to inputs. | About interpretability, not application runtimes. |
| **Lightweight Neural App Control (LiMAC)** | 2024 | Projects hidden states into UI-element embedding space. | Tiny, not a full runtime. |
| **Physics of Language Models Part 1** | 2024 | Hidden states encode hierarchical grammar-like structure. | Analysis of representational capacity, not systems design. |

**Research synthesis:** The intersection of world models + LaSynth-style latent execution + transformer-state/KV-cache theory is the academic lineage for projection-based apps. Nothing surveyed has been pushed into the full application domain yet.

---

## 4. The Gap Analysis

### What's Missing (Both Sessions Agree)

| Gap | What exists today | What's needed |
|---|---|---|
| **Persistent internal state with identity** | Prompt context, memory blocks, databases, files, symbolic world models | Recurrent hidden state / KV-cache state as the durable application object |
| **Stable projection function** | Text generation, declarative UI specs, explicit HTML/apps | Hidden state → deterministic(near-deterministic) projection operator → UI surface |
| **Separation between app identity and artifact** | Artifact IS code/schema/markup/transcript | Artifacts are views, not the app itself |
| **Debuggability without symbolic fallback** | Explicit structure (memory blocks, typed events, JSON-RPC) | Latent probes, causal intervention on internal state, projection diagnostics, activation-level snapshotting |
| **Multi-user / transactional semantics** | No one solves this | Concurrent edits against neural state, transactional consistency, authorization over latent subspaces |

### Four Open Problems

| Problem | SOTA | What's missing |
|---|---|---|
| Persistent state in latents | Genie 3: ~1 minute consistency. MemGPT: externalizes state. | No model holds business-application state (users, records, workflow) reliably for hours/days inside weights or KV cache. |
| Projection from state to UI | A2UI, AG-UI, Mirage, Thesys C1 | None treats UI as a learned function of hidden state. Need state → UI directly (potentially via a learned decoder over activations). |
| Verifiability / auditing | Letta memory blocks, AG-UI typed events, MCP JSON-RPC | A model whose hidden state IS the app is a black box. No work on "auditing the running state of a neural app." |
| Interaction latency | GameNGen/Oasis: 20fps for video. Mirage: seconds-per-click. | No latency-acceptable projection-based productivity app exists today. |

---

## 5. Thesis Candidates (Formulated from Both Sessions)

### Thesis 1
Projection-based applications are a plausible software category distinct from codegen, agentic UI, and generative UI, because the strong version relocates application semantics from explicit code/schema layers into persistent neural state.

### Thesis 2
The nearest academic ancestors are latent world models and neural program induction, not frontend generation systems.

### Thesis 3
The main blockers are not model capability alone; they are runtime architecture problems: persistence, observability, concurrency, determinism, security, projection design.

### Thesis 4 (from Opus session only)
The strongest argument *for* projection-based apps is analogical: world models and neural game engines show that networks can function as interactive runtimes in visual domains. The strongest argument *against* is that business applications need explicit invariants, auditability, transactions, and permissions, and no published technique found guarantees those inside a network's hidden state.

---

## 6. Best Current Ingredients for a Prototype

If someone wanted to prototype this today, the closest ingredients from existing work:

1. **World-model latent state** — from World Models / Dreamer-style research
2. **Persistent agent memory** — from MemGPT / Letta-style architectures
3. **Projection surface protocols** — from SLOP for semantic state/affordances; AG-UI, A2UI, or MCP Apps for UI/host surfaces
4. **Interpretability / decodability tools** — from DecNN, mechanistic interpretability, probe-based analysis
5. **Mirage pattern** — re-derive each tick from interaction history, no persistent code layer

SLOP is the strongest local candidate for the **weak/hybrid projection protocol boundary**: live semantic state tree, contextual affordances, salience, snapshots, patches, and model-context injection. It should be treated as explicit-state infrastructure, not as proof of a neural app runtime; see [`slop-fit.md`](slop-fit.md).

But combining these ingredients would still produce a **hybrid system** unless state were deliberately kept *inside* the model rather than mirrored into explicit stores and schemas.

---

## 7. Source Index (Consolidated)

### Karpathy
- Software 2.0: https://karpathy.medium.com/software-2-0-a64152b37c35
- YC AI Startup School 2025: https://www.latent.space/p/s3
- AI Ascent 2026 / MenuGen framing (secondary recap; needs primary transcript/video before use as strong evidence)
- "People spirits" / simulators: https://x.com/karpathy/status/1997731268969304070
- "LLM as kernel": https://x.com/karpathy/status/1707437820045062561

### Working Artifacts
- Mirage / Among AI (Dec 2025): https://amongai.com/2025/12/10/hallucinate-any-app-one-screen-at-a-time/
- GameNGen (Google, 2024): https://arxiv.org/abs/2408.14837, https://gamengen.github.io/
- Decart Oasis 2.0: https://oasis-model.github.io/
- DeepMind Genie 3: https://deepmind.google/blog/genie-3-a-new-frontier-for-world-models/
- Websim: https://websim.com/
- Sora / Sora 2: https://openai.com/index/video-generation-models-as-world-simulators/

### Protocols
- AG-UI: https://docs.ag-ui.com/introduction
- A2UI (Google): https://a2ui.org/, https://developers.googleblog.com/introducing-a2ui-an-open-project-for-agent-driven-interfaces/
- MCP Apps (Anthropic): https://blog.modelcontextprotocol.io/posts/2026-01-26-mcp-apps/
- Thesys C1: https://www.thesys.dev/, https://docs.thesys.dev/guides/how-c1-works
- CopilotKit: https://www.copilotkit.ai/, https://github.com/CopilotKit/generative-ui

### Academic
- RobustFill (Microsoft, 2017): https://www.microsoft.com/en-us/research/publication/robustfill-neural-program-learning-noisy-io/
- Neural Program Lattices (Microsoft, 2017): https://www.microsoft.com/en-us/research/publication/neural-program-lattices/
- Program Synthesis with LLMs (2021): https://huggingface.co/papers/2108.07732
- RASP (2021): https://arxiv.org/pdf/2106.06981
- Decodable Neural Networks (2021): https://arxiv.org/pdf/2106.00769
- World Models (Ha & Schmidhuber, 2018): https://worldmodels.github.io/
- Dreamer (2019): https://huggingface.co/papers/1912.01603
- Learning by Abstraction / Neural State Machine (NIPS 2019): https://papers.nips.cc/paper_files/paper/2019/hash/c20a7ce2a627ba838cfbff082db35197-Abstract.html
- From Word Models to World Models (2023): https://huggingface.co/papers/2306.12672
- LLMs for PDDL World Models (ICML 2023): https://icml.cc/virtual/2023/27213
- MemGPT (2023): https://arxiv.org/abs/2310.08560
- StateFlow (2024): https://huggingface.co/papers/2403.11322
- Physics of Language Models Part 1 (2024): https://arxiv.org/pdf/2305.13673
- LaSynth (NeurIPS 2021): https://arxiv.org/abs/2107.00101
- Transformers are Multi-State RNNs (2024): https://arxiv.org/html/2401.06104v1
- Generating GUIs (CHI 2025): https://dl.acm.org/doi/10.1145/3706599.3719743
- LiMAC (2024): https://arxiv.org/html/2410.17883v1

### Startups / Companies
- Letta: https://www.letta.com/, docs: https://docs.letta.com/guides/agents/memory
- Wordware: https://www.wordware.ai/
- Agentplace: https://qa.agentplace.io/
- World Labs: https://www.worldlabs.ai/
- AMI Labs: https://techcrunch.com/2026/01/23/whos-behind-ami-labs-yann-lecuns-world-model-startup/
- Transient AI: https://transient.ai/
- Inworld AI: https://inworld.ai/

### Related Papers
- State Machine of Thoughts (2023): https://papers.cool/arxiv/2312.17445
- Extracting Reduced Logic Programs (2008): https://jens-lehmann.org/files/2008/ann_extraction.pdf
- Web World Models: https://liner.com/review/web-world-models
- Computer-Using World Model (2026): https://huggingface.co/papers/2602.17365
- Generative Agents (2023): https://huggingface.co/papers/2304.03442
- LLM Applications: Paradigms and Next Frontier (2025): https://arxiv.org/html/2503.04596v2
- Is Sora a World Simulator? (2024): https://arxiv.org/html/2405.03520v1
- Understanding World or Predicting Future? (ACM CSUR 2025): https://github.com/tsinghua-fib-lab/World-Model

---

## 8. Original Research Artifacts

These are preserved as standalone model-assisted research notes. They are useful for comparing perspectives, but they should not be treated as independent empirical confirmation because the prompts were nearly identical.

- **Broad survey run** — `experiments/codex-research-gpt55.md`
  - 443 lines, 33 sources, 5-category survey framework
  - Strengths: broad coverage, systematic categorization
  - Bias tendency: more systematic, less critical analysis

- **Critical synthesis run** — `experiments/codex-research-opus.md`
  - 267 lines, 8 anchor citations, deep critical analysis
  - Strengths: sharper thesis formulation, identifies Mirage as the closest weak-projection demo, provides honest critical assessment
  - Bias tendency: more skeptical, more precise in gap analysis

For citation hygiene and manual-check notes, see `source-status.md`.
