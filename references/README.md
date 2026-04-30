# References — Research Survey

## 1. Theoretical Foundations

### 1.1 Software 1.0 → 2.0 → 3.0 (Karpathy, 2017–2026)

**Source:** [Software 2.0 — Karpathy Blog, Nov 2017](https://karpathy.medium.com/software-2-0-a64152b37c35)

> "Software 1.0 consists of explicit instructions to the computer written by a human programmer in a language that is friendly to the computer. Software 2.0 can be written in much more abstract, human unfriendly language, such as the weights of a neural network."

**Key insight:** Neural network weights are code — just not human-readable code. They encode behavior through numerical parameters rather than symbolic instructions. The program exists; it's stored in a form that no human can directly inspect.

**Evolution:**
- **Software 1.0:** Programmer writes code → code executes
- **Software 2.0:** Programmer curates data + trains → weights encode the program
- **Software 3.0 (2026):** Programmer directs agents → agents generate and verify code autonomously

### 1.2 Neural Network Weights as Program Representation

**Source:** [Hassabis, Demis. "AI and the Future of Science" — various talks 2024–2026]

Demis Hassabis has articulated the view that neural networks don't just approximate functions — they *learn* representations of the world. The network's internal state encodes a model of reality, not just input-output mappings. This is critical for the proj concept: the model doesn't just "know" how to respond — it has an internal understanding of the domain.

### 1.3 LLMs as World Models (LeCun Critique)

**Source:** Yann LeCun's critiques of LLM limitations (2024–2025), various talks and papers

LeCun argues that LLMs lack world models and true reasoning — they're "stochastic parrots." This critique is important for proj because it defines the boundaries of what can live in the weights. If LLMs truly lack world models, the "app" they project will be fundamentally limited in its ability to maintain consistent internal state across interactions.

**Counter-point:** Karpathy's position is more pragmatic — even without perfect reasoning, LLMs are powerful enough to be useful if you build the right interaction patterns around them.

### 1.4 Internal State Representation in LLMs

**Source:** [Do LLMs Build World Representations? — NeurIPS 2024](https://proceedings.neurips.cc/paper_files/paper/2024/file/b1b16c4b875eb84d3585cb70d23970ca-Paper-Conference.pdf)

> "We propose a new framework to probe the abstract world state in LLM representations through the lens of state abstraction. Experiments demonstrate that LLMs tend to preserve a goal-oriented world abstraction instead of a more general one during decoding."

This paper directly supports the proj thesis: LLMs do build internal state representations. They abstract away irrelevant details and maintain goal-oriented models of the world during decoding.

**Source:** [LLMs Know More Than They Show — OpenReview](https://openreview.net/forum?id=KRnsX5Em3W)

> "The internal representations of LLMs encode much more information about truthfulness than previously recognized."

The model's internal state contains information that its output doesn't fully express. This gap between internal state and output is the space where proj operates — the projection is a rendering of what's inside.

## 2. Existing Systems in This Space

### 2.1 Generative UI (Google, 2025)

**Source:** [Google Research Blog — Generative UI, Nov 2025](https://research.google/blog/generative-ui-a-rich-custom-visual-interactive-user-experience-for-any-prompt/)

Google's Gemini app generates entire user experiences (web pages, games, tools) from user prompts. The model outputs HTML/CSS/JS that the browser renders.

**How it relates to proj:** Generative UI is the closest existing system to proj, but it's fundamentally different in architecture:
- Generative UI: Model generates **HTML** → browser renders it. The HTML is the output, not the state.
- proj: Model *is* the state. The UI is a rendering of the model's internal representation, not a generated HTML file.

In Generative UI, the model doesn't maintain persistent internal state. Each interaction is roughly self-contained. In proj, the model's weights + context *are* the application.

**Source:** [Google's PAGE Evaluation Dataset](https://generativeui.github.io/)

Google created PAGE, a dataset of human expert-made websites, to evaluate Generative UI against. Results showed Generative UI ranked "closely behind human-expert-designed websites."

### 2.2 A2UI (Google, 2025)

**Source:** [Introducing A2UI — Google Developers Blog, Dec 2025](https://developers.googleblog.com/introducing-a2ui-an-open-project-for-agent-driven-interfaces/)

A2UI is a declarative data format for agent-generated UIs. Agents send JSON describing component trees; a client renders them using native components.

**How it relates to proj:** A2UI is about agents generating UI *data* (not executable code) to render in a client. It's a protocol for structured UI communication. It's closer to proj than Generative UI because it treats UI as a structured representation rather than raw HTML. However, it still assumes a fixed client with predefined components. The model doesn't "know" the app — it sends a message telling a client what to render.

In proj, the model's entire internal state IS the app. The projection is a real-time rendering of that state.

### 2.3 AG-UI Protocol

**Source:** [AG-UI Protocol — GitHub](https://github.com/ag-ui-protocol/ag-ui/)

AG-UI is an open, lightweight, event-based protocol for AI agent to user interaction. It standardizes how agents connect to user-facing applications.

**How it relates to proj:** AG-UI is the plumbing layer between agents and UIs. It could be the transport layer for proj projections. But AG-UI itself is agnostic to what the agent "knows" — it just transports UI events and data.

### 2.4 LLM State Representation (LLM-State)

**Source:** [LLM-State: Expandable State Representation for Long-horizon Tasks](https://arxiv.org/abs/2311.17406)

Encodes observations into state representations, where LLMs generate code to consistently estimate and track object attributes.

**Relevance to proj:** This is about giving LLMs a structured way to maintain state across interactions. For proj, the challenge is the opposite: the LLM's weights already contain knowledge; the question is maintaining *application-specific* state across sessions.

### 2.5 Memori: Persistent Memory Layer

**Source:** [Memori — arXiv 2603.19935](https://arxiv.org/html/2603.19935)

External memory engine for LLM agents. Solves the statelessness problem by providing persistent, meaningful context across interactions.

**Relevance to proj:** Directly addresses the state management problem. If the model's weights are the app, Memori provides the memory that keeps the app state consistent across turns.

### 2.6 LLM Applications: Current Paradigms and Next Frontier

**Source:** [Hou, Zhao, Wang — arXiv 2503.04596, Oct 2025](https://arxiv.org/html/2503.04596v2)

Comprehensive analysis of four LLM application paradigms: App Stores, Agents, Self-Hosted Services, and LLM-Powered Devices. Proposes a three-layer architecture (Infrastructure, Protocol, Application).

**Relevance to proj:** This paper maps the landscape that proj operates in. The key gap they identify — fragmentation and lack of interoperability — is exactly what a projection-based runtime needs to solve. The paper argues that future applications require "stronger model capabilities, robust architectures, and sustainable ecosystems."

## 3. The Research Gap

### 3.1 What No One Has Built Yet

The gap between existing systems and the proj concept:

| System | What it does | What proj needs |
|--------|-------------|-----------------|
| Generative UI | Model generates HTML | Model *is* the state, HTML is a projection |
| A2UI | Agent sends component data | Model *has* the app internally |
| AG-UI | Protocol for agent↔UI events | Protocol for projection↔internal state |
| Memori | External memory for agents | Memory as part of the neural state |
| Cursor/Copilot | AI writes code files | AI *is* the program, code is projection |

### 3.2 Why This Gap Exists

1. **Models weren't good enough.** Until ~2025, LLMs couldn't maintain coherent internal app state across long interactions. They forgot, drifted, and hallucinated. The projection would diverge from the intended state.

2. **The infrastructure doesn't exist.** No framework provides a structured way for a model to maintain and mutate its own internal state as an application. Frameworks like LangChain treat the model as a function call, not as the app itself.

3. **No one has framed it this way.** People have been building "agentic apps" and "generative UI" — but not as a unified runtime where the model's internal state *is* the application.

4. **The evaluation problem.** How do you test a system where there's no code to test? Traditional software testing doesn't apply. You need property-based testing of the projection vs. the internal state.

### 3.3 Why Now

1. **Model capabilities:** Current models (Claude Opus 4.6, GPT-5.3-Codex, Gemini 3 Pro) can maintain coherent state across much longer interactions than 2 years ago. The "jaggedness" is decreasing.

2. **The agent ecosystem is maturing:** A2UI, AG-UI, MCP, and the agent protocol space are converging on standards. This creates the infrastructure layer that proj can build on.

3. **Karpathy's autoresearch proves the loop works:** 700 experiments in 2 days, 11% speedup. Autonomous agent loops are no longer theoretical — they're engineering problems.

4. **Developer fatigue:** Traditional app development is reaching diminishing returns. The market is ready for a paradigm shift.

## 4. What proj Would Look Like

### 4.1 Architecture (Conceptual)

```
┌──────────────────────────────────────────────────────┐
│                    User Interface                     │
│              (projection / rendered view)              │
└──────────────────────────┬───────────────────────────┘
                           │  Projection Protocol
                           ▼
┌──────────────────────────────────────────────────────┐
│              Projection Layer                         │
│  ┌─────────┐  ┌──────────┐  ┌────────────────────┐  │
│  │  Render  │  │ Validate │  │  State Transform   │  │
│  │  Engine  │  │  Engine  │  │    Engine          │  │
│  └────┬─────┘  └──────────┘  └────────┬───────────┘  │
└───────┼───────────────────────────────┼──────────────┘
        │                               │
        ▼                               ▼
┌──────────────────────────┐    ┌─────────────────────────┐
│  Neural Network (Weights) │    │  Persistent State       │
│  ┌──────────────────────┐ │    │  (across sessions)      │
│  │ Internal representation│ │    │  ┌──────────────────┐ │
│  │ of application logic  │ │    │  │ Structured state  │ │
│  │ + data + behavior     │ │    │  │ maintained by     │ │
│  │ (the actual "app")    │ │    │  │ model + external  │ │
│  └──────────────────────┘ │    │  └──────────────────┘ │
└──────────────────────────┘    └─────────────────────────┘
```

### 4.2 Key Components

1. **State Engine:** Manages the model's internal representation of the application. Not just context window management — a structured representation of the app's domain logic, data, and state machine.

2. **Projection Renderer:** Takes the current internal state and generates a user-facing interface. Could be text, HTML, structured data, voice, whatever format the user prefers.

3. **Validation Layer:** Verifies that the projection faithfully represents the internal state. Catches hallucination, drift, and inconsistency.

4. **State Persistence:** Allows the app to maintain state across sessions. Could be weight-based (fine-tuned for a specific app) or context-based (structured state passed in prompts).

### 4.3 Why This Is Hard

1. **State coherence:** The model must maintain a consistent, mutable internal state across interactions. Current models forget, drift, and contradict themselves.

2. **Projection fidelity:** The UI must be a faithful rendering of the internal state. If the model "thinks" one thing but renders another, the user is confused and the app is broken.

3. **Verification:** How do you verify a system where there's no source code? You need new kinds of testing — property-based tests on the projection, consistency checks between internal state and rendered output.

4. **Determinism vs. creativity:** Apps need deterministic behavior (click this button, get this result). LLMs are inherently probabilistic. You need a way to balance consistency with flexibility.

## 5. SLOP Integration

This project connects directly to the SLOP protocol:

- **Session provider layer** — The persistent state management that keeps the app alive across interactions.
- **Runtime** — The execution environment where the model processes interactions and maintains state.
- **Orchestration** — The layer that coordinates between the projection renderer, validation engine, and state manager.
- **Protocol** — The interface between the model's internal state and external consumers.

proj is essentially a use case for SLOP: a protocol for building neural-native applications where the runtime manages the model's state as the application itself.

## References

1. Karpathy, A. (2017). "Software 2.0." [Medium](https://karpathy.medium.com/software-2-0-a64152b37c35)
2. Karpathy, A. (2026). "From Vibe Coding to Agentic Engineering." Sequoia AI Ascent 2026. YouTube: `96jN2OCOfLs`
3. Google Research (2025). "Generative UI: A rich, custom, visual interactive user experience for any prompt." [Blog](https://research.google/blog/generative-ui-a-rich-custom-visual-interactive-user-experience-for-any-prompt/)
4. Google Developers (2025). "Introducing A2UI: An open project for agent-driven interfaces." [Blog](https://developers.googleblog.com/introducing-a2ui-an-open-project-for-agent-driven-interfaces/)
5. Hou, X., Zhao, Y., Wang, H. (2025). "LLM Applications: Current Paradigms and the Next Frontier." arXiv:2503.04596
6. NeurIPS 2024. "Do LLMs Build World Representations? Probing Through the Lens of State Abstraction."
7. OpenReview. "LLMs Know More Than They Show: On the Intrinsic Representation of LLMs."
8. arXiv 2603.19935. "Memori: A Persistent Memory Layer for Efficient, Context-Aware LLM Agents."
9. arXiv 2311.17406. "LLM-State: Expandable State Representation for Long-horizon Task Execution."
10. AG-UI Protocol. [GitHub](https://github.com/ag-ui-protocol/ag-ui/)
11. A2UI. [GitHub](https://github.com/google/A2UI/)
12. Karpathy Loop / Autoresearch. [GitHub](https://github.com/karpathy/autoresearch)
