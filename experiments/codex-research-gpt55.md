# Neural App Runtime / Projection-Based Applications

Date: 2026-04-30

> **Audit note:** This is a preserved raw model-assisted research artifact. Some phrasing is intentionally left as originally generated. Use `../references/consolidated-research.md` as the canonical synthesis and `../references/source-status.md` for citation hygiene/corrections.

## Working Definition

This memo studies a specific hypothesis:

- A **projection-based application** is an application where the model's internal state is the application runtime.
- The user interface is a **projection/rendering** of that state.
- There is no durable, explicit application logic layer between user and app in the ordinary sense of:
  - hand-authored business logic
  - declarative UI schemas as the source of truth
  - code-defined state machines
  - external symbolic world models that actually hold the app's semantics

This is stricter than:

- generative UI
- agent-to-UI protocols
- codegen agents
- LLM agents with tools
- apps with persistent memory
- apps with code-defined state and model-assisted rendering

## Bottom Line

After surveying academic work, protocol work, systems, and startups, I did **not** find a mature system that fully matches the projection concept.

What exists today clusters into five nearby but distinct camps:

1. **Neural program synthesis / induction**
   - Models generate code, programs, or actions.
   - The runtime still lives outside the model.
2. **Neuro-symbolic extraction / abstraction**
   - Researchers try to recover symbolic programs, rules, or state machines from nets.
   - This is almost the inverse of the projection idea: it translates neural state back into explicit programs.
3. **World-model systems**
   - Neural latent state becomes a planning substrate.
   - But the "application" is usually a simulator, agent policy, or environment model, not a user-facing software runtime.
4. **Generative UI / agentic UI protocols**
   - These allow models or agents to choose or stream interfaces.
   - But the UI is still rendered through explicit schemas, component catalogs, iframes, or event protocols.
5. **Persistent-memory agents / AI-native app startups**
   - These make agents stateful and adaptive.
   - But memory is externalized into stores, blocks, files, databases, or code-defined containers.

So the strongest conclusion is:

- The field has many **adjacent primitives** for projection-based software.
- The field does **not yet have** a canonical architecture where the model's hidden state itself is the app runtime and the UI is merely a direct projection of that runtime.

## Comparison Rubric

For each item below, I evaluated:

- **State location**: weights, activations/context, external memory, code, symbolic graph, or database
- **UI source**: text, component schema, iframe app, code-generated app, or no UI focus
- **Gap to projection concept**: what still exists as an explicit mediating layer

## A. Academic Foundations

### 1. Andrej Karpathy, "Software 2.0"
- URL: https://karpathy.medium.com/software-2-0-a64152b37c35
- Date: 2017-11-11
- Summary: Karpathy's core claim is that neural network weights are a new kind of software artifact. The training process becomes the compiler; data becomes a primary programming medium.
- Analysis: This is the cleanest intellectual predecessor. But "Software 2.0" still mainly argues that weights are code. It does not yet fully specify a user-facing application model where activations and internal neural state become the runtime and interface source directly.

### 2. RobustFill: Neural Program Learning under Noisy I/O
- URL: https://www.microsoft.com/en-us/research/publication/robustfill-neural-program-learning-noisy-io/
- Date: 2017-03
- Summary: Compares neural program synthesis and neural program induction for string transformation tasks.
- Analysis: Important because it distinguishes **synthesizing explicit programs** from **latent program induction**. Projection-based apps are closer to induction than synthesis. But RobustFill still studies narrow transformations, not persistent application state or UI projection.

### 3. Neural Programmer-Interpreter / Neural Program Lattices
- URL: https://www.microsoft.com/en-us/research/publication/neural-program-lattices/
- Date: 2017-03
- Summary: Learns program structure compositionally from weak supervision, using hierarchical neural control.
- Analysis: Relevant because it treats neural systems as executors of latent procedural structure. Still, the end goal is recoverable task structure and execution over external environments. It is not a model-as-app-runtime architecture.

### 4. Program Synthesis with Large Language Models
- URL: https://huggingface.co/papers/2108.07732
- Date: 2021-08-16
- Summary: Evaluates LLMs on synthesis of short Python programs from natural language.
- Analysis: Useful as a boundary marker. This is still firmly in the "model writes code" paradigm. Projection-based apps explicitly reject this mediation layer.

### 5. Thinking Like Transformers / RASP
- URL: https://arxiv.org/pdf/2106.06981
- Date: 2021-07-19
- Summary: Proposes RASP as a symbolic programming abstraction for transformer computations.
- Analysis: Important because it shows transformer behavior can sometimes be described as an interpretable program. But again, this moves from neural computation toward explicit symbolic representation. It helps understand projection architectures, but it is not one.

### 6. Decodable Neural Networks
- URL: https://arxiv.org/pdf/2106.00769
- Date: 2021-10-26
- Summary: Jointly trains neural networks so activations decode back to inputs, making representations more inspectable and composable.
- Analysis: Highly relevant to "projection" in a literal sense. If internal activations can be decoded meaningfully, UI could be a rendering of those states. But this work is about interpretability and compositionality, not user-facing application runtimes.

### 7. From Word Models to World Models
- URL: https://huggingface.co/papers/2306.12672
- Date: 2023-06-22
- Summary: Uses LLMs to translate language into probabilistic programs that support reasoning over explicit world models.
- Analysis: This is one of the closest conceptual neighbors, but it still externalizes state into probabilistic programs. The application semantics live in that symbolic substrate, not in the model's hidden state.

### 8. Leveraging Pre-trained LLMs to Construct and Utilize World Models for Model-based Task Planning
- URL: https://icml.cc/virtual/2023/27213
- Date: 2023
- Summary: Uses LLMs to generate PDDL world models and then relies on classical planners for execution.
- Analysis: This is explicitly anti-projection. The model bootstraps a symbolic runtime, then hands control to a formal planner. Strong evidence that most current systems still want an explicit, inspectable intermediate layer.

### 9. MemGPT: Towards LLMs as Operating Systems
- URL: https://arxiv.org/abs/2310.08560
- Date: 2023-10-12
- Summary: Introduces hierarchical memory management for LLMs, inspired by operating systems.
- Analysis: One of the most important state-management papers for this topic. But MemGPT does not make the model's internal state the application. It manages scarce context by paging data between explicit memory tiers.

### 10. Generative Agents: Interactive Simulacra of Human Behavior
- URL: https://huggingface.co/papers/2304.03442
- Date: 2023-04-07
- Summary: LLM-driven agents maintain memories, reflections, and plans in an interactive simulation environment.
- Analysis: Closer to "world models as applications" than most software papers. But the architecture still depends on explicit memory streams, planners, and environment state. The agent is not the whole app; it is an actor inside a separately modeled world.

### 11. StateFlow: Enhancing LLM Task-Solving through State-Driven Workflows
- URL: https://huggingface.co/papers/2403.11322
- Date: 2024-03-17
- Summary: Frames LLM task solving as a state machine with explicit transitions and state-grounded subtasks.
- Analysis: Strong evidence that the industry instinct remains to recover explicit control structure around LLMs. Useful for reliability, but opposite to the "hidden state is the app" thesis.

### 12. Learning by Abstraction: The Neural State Machine
- URL: https://papers.nips.cc/paper_files/paper/2019/hash/c20a7ce2a627ba838cfbff082db35197-Abstract.html
- Date: 2019
- Summary: Learns an abstract semantic graph and performs sequential reasoning over it.
- Analysis: Relevant because it uses an intermediate "world model" with state-like traversal. But the state is an explicit graph abstraction, not a raw neural hidden state exposed through projection.

### 13. World Models
- URL: https://huggingface.co/papers/1803.10122
- Date: 2018-03-27
- Summary: Learns latent dynamics for environments and trains policies inside imagined rollouts.
- Analysis: This is foundational for the "internal state as environment runtime" idea. But it targets control and planning, not interactive software surfaces. The user does not directly inhabit a projection of the latent state in an application sense.

### 14. Dream to Control: Learning Behaviors by Latent Imagination
- URL: https://huggingface.co/papers/1912.01603
- Date: 2019-12-03
- Summary: Learns policies using imagined trajectories in a latent world model.
- Analysis: Strongest evidence from RL that latent state can act like a runtime substrate. Still, the substrate is optimized for policy learning, not user-visible software semantics.

### 15. Physics of Language Models: Part 1
- URL: https://arxiv.org/pdf/2305.13673
- Date: 2024-06-02 version noted on arXiv
- Summary: Studies how transformer hidden states encode hierarchical grammar-like structure.
- Analysis: Important because it suggests hidden states can represent structured algorithmic processes internally. That supports plausibility for projection-based apps. But it remains analysis of representational capacity, not systems design.

### 16. Extracting Reduced Logic Programs from Neural Networks
- URL: https://jens-lehmann.org/files/2008/ann_extraction.pdf
- Date: 2008
- Summary: Classic neural-symbolic work on recovering logic programs from trained neural networks.
- Analysis: This is almost the philosophical opposite of projection-based apps. Instead of accepting neural state as the runtime, it tries to reconstruct explicit symbolic runtime artifacts from it. The paper matters because it shows the long-standing discomfort with leaving semantics "inside the net."

## B. Systems and UI Architectures

### 17. Web World Models
- URL: https://liner.com/review/web-world-models
- Date: 2025-12-29
- Summary: Proposes a middle ground where world state and "physics" remain in ordinary web code while LLMs generate narrative/context over that structure.
- Analysis: Extremely relevant because it names the exact compromise most builders are choosing. It is not projection-based. It explicitly argues for code-defined rules plus model-driven imagination, which is a hybrid rather than a neural runtime.

### 18. Computer-Using World Model
- URL: https://huggingface.co/papers/2602.17365
- Date: 2026-02-19
- Summary: Builds a world model for desktop software use, predicting UI state changes and helping agents reason about consequences.
- Analysis: Important because it treats software UIs as environments with latent dynamics. But the goal is better control of existing software, not replacement of the application layer by neural state.

### 19. OpenGenerativeUI / raw HTML widget generation
- URL: https://github.com/CopilotKit/generative-ui
- Date: repository crawled 2026
- Summary: Demonstrates open-ended generative UI where agents can emit raw HTML/SVG/canvas content for rendering.
- Analysis: This looks closer to "projection" than component catalogs do, but it is still content generation, not projection of a durable internal app state. The output is still an artifact, not the app's underlying runtime.

### 20. Tambo
- URL: https://tambo.co/
- Date: crawled 2026
- Summary: Toolkit for agents that render existing React components and update state through those components.
- Analysis: Useful example of AI-native UI that still anchors on developer-owned components and state. It is not projection-based because the app logic remains in React and component contracts.

### 21. Thesys C1
- URL: https://docs.thesys.dev/guides/how-c1-works
- Date: crawled 2026
- Summary: Middleware turns LLM responses into a UI specification object rendered by a client component.
- Analysis: Clear example of a declarative schema boundary. The model chooses UI, but the schema is the contract. Projection-based apps would want less mediation than this.

### 22. CopilotKit Generative UI
- URL: https://www.copilotkit.ai/
- Date: crawled 2026-04-30
- Summary: Positions itself as an agentic frontend stack spanning AG-UI, A2UI, MCP, persistence, and multimodal user-agent interaction.
- Analysis: Strong infrastructure for agentic applications, but it standardizes the boundary between agents and UIs rather than dissolving it. This is an enabling layer for projection experiments, not the concept itself.

## C. Protocol Work

### 23. AG-UI
- URL: https://docs.ag-ui.com/introduction
- Date: crawled 2026
- Summary: Event-based protocol connecting agent runtimes to user-facing applications, including state deltas, tool events, and multimodal streaming.
- Analysis: AG-UI assumes a separation between agent backend and user-facing app. It is designed to synchronize them. That is useful operationally, but it preserves the very interface boundary projection-based apps would try to collapse.

### 24. A2UI
- URL: https://a2ui.org/
- Date: crawled 2026-04-30
- Summary: Declarative protocol for agent-generated native UI across platforms using a component catalog and streaming updates.
- Analysis: This is the cleanest contrast case. A2UI lets the model decide UI structure, but only through pre-approved components and schemas. The runtime is still host-owned. Projection-based apps would want the model state itself, not a declarative description, to be the primary application artifact.

### 25. MCP Apps
- URL: https://blog.modelcontextprotocol.io/posts/2026-01-26-mcp-apps/
- Date: 2026-01-26
- Summary: Official MCP extension for interactive tool-returned UIs rendered in sandboxed iframes.
- Analysis: MCP Apps are open-ended on the surface, but they actually increase mediation: UI is an explicit HTML artifact served via `ui://`, rendered in an iframe, and connected via JSON-RPC. Very useful, but far from hidden-state-as-app.

### 26. MCP Framework overview of Apps
- URL: https://www.mcp-framework.com/docs/apps/overview
- Date: crawled 2026
- Summary: Describes how tools register `ui://` resources, hosts render them, and iframe-host communication occurs over JSON-RPC.
- Analysis: This is a protocolized delivery system for app fragments. It proves the ecosystem is standardizing the transport layer, not replacing the application layer with neural state.

## D. Startups / Company Directionality

### 27. Letta
- URL: https://www.letta.com/
- Date: crawled 2026-04-29
- Summary: "Memory-first" persistent agents with structured memory blocks, archival memory, and stateful agents-as-services.
- Analysis: Probably the most important company in the state-management cluster. Letta gets closer to long-lived neural applications, but it still externalizes memory aggressively. The agent is persistent, yet the app state is not simply the model's hidden state.

### 28. Wordware
- URL: https://www.wordware.ai/
- Date: crawled 2026-04-30
- Summary: Builds around the thesis that words are the next programming language and context compounds over time.
- Analysis: More about language-native development and agent composition than model-internal runtimes. Useful ideological neighbor, not a projection implementation.

### 29. Agentplace
- URL: https://qa.agentplace.io/
- Date: crawled 2026
- Summary: Markets "web agents and AI-native apps" with LLM-centered architecture, MCP integrations, and dynamic UI behavior.
- Analysis: The stack still includes a builder, integrations, rendering blocks, and browser-side capabilities. This is AI-native orchestration, not direct state projection.

### 30. World Labs
- URL: https://www.worldlabs.ai/
- Date: crawled 2026
- Summary: Builds spatial-intelligence models that generate and edit persistent 3D worlds.
- Analysis: Very relevant if projection-based applications expand beyond productivity software into spatial software. Still, World Labs is building world models and editable generated environments, not user apps whose runtime is the model's internal state in the software-product sense.

### 31. AMI Labs
- URL: https://techcrunch.com/2026/01/23/whos-behind-ami-labs-yann-lecuns-world-model-startup/
- Date: 2026-01-23
- Summary: Yann LeCun's startup explicitly focuses on world models that understand the real world beyond language.
- Analysis: Strategically important because it shifts attention from text interfaces to internal environmental models. But current public framing is still around world understanding and downstream verticals, not projection-based apps.

### 32. Transient AI
- URL: https://transient.ai/
- Date: crawled 2026
- Summary: Markets a "Declarative AI OS" and discusses moving beyond chatbox interfaces toward generative UI and "liquid software."
- Analysis: Strong rhetorical overlap with projection-based apps. Still appears to rely on declarative orchestration and generated interface layers rather than abolishing explicit application mediation.

## E. State Representation and Persistent Memory

### 33. Letta Memory Model
- URL: https://docs.letta.com/guides/agents/memory
- Date: crawled 2026
- Summary: Distinguishes core memory blocks from external archival memory and frames memory as context-window management.
- Analysis: Good practical evidence that stateful AI systems today depend on explicit memory architecture. Projection-based apps would need to either absorb this into the model or accept hybridization.

### 34. Letta Core Concepts
- URL: https://docs.letta.com/core-concepts
- Date: crawled 2026
- Summary: Treats agents as persistent services with database-backed state and multi-application access.
- Analysis: This is service-oriented statefulness, not latent-runtime statefulness. It is operationally viable, but conceptually conservative relative to the projection thesis.

### 35. State Machine of Thoughts
- URL: https://papers.cool/arxiv/2312.17445
- Date: 2023-12-29
- Summary: Records successful and failed reasoning trajectories as a reusable state machine.
- Analysis: Another example of the field converting fluid model behavior into explicit state structures for reuse and control. Good for reliability, but it works against pure projection.

## Synthesis: What Is Missing

Across the literature and systems landscape, the missing ingredients for a true neural app runtime are:

### 1. Persistent internal state with identity

Current systems generally persist state in:

- prompt context
- memory blocks
- databases
- files
- symbolic world models
- UI schemas

Very few systems treat recurrent hidden state, KV-cache state, or latent dynamical state as the durable application object.

### 2. A stable projection function from model state to interface

Existing systems mostly do one of three things:

- generate text
- emit declarative UI specs
- emit explicit HTML/apps

A projection-based application would need something more like:

- hidden/app state -> deterministic or near-deterministic projection operators -> UI surface

That is closer to graphics rendering or state-space observation than to content generation.

### 3. Separation between app identity and generated artifact

Today the visible artifact is usually:

- code
- schema
- markup
- an agent transcript

In a projection app, those artifacts are views, not the app itself.

### 4. Debuggability without symbolic fallback

Almost every serious system introduces explicit structure because builders need:

- observability
- rollback
- safety checks
- reproducibility
- testing

Projection-based apps need a new debugging model, likely based on:

- latent probes
- causal intervention on internal state
- explicit projection diagnostics
- state snapshotting at the activation or memory level

### 5. Multi-user and transactional semantics

Nothing surveyed really solves:

- concurrent edits against neural internal state
- transactional consistency
- authorization over latent subspaces
- schema evolution without schemas

This is one reason current companies externalize state.

## Best Current Proxies

If someone wanted to prototype this idea today, the closest ingredients from existing work would be:

1. **World-model latent state**
   - from World Models / Dreamer-style research
2. **Persistent agent memory**
   - from MemGPT / Letta-style architectures
3. **Projection surface protocols**
   - from AG-UI, A2UI, or MCP Apps
4. **Interpretability / decodability tools**
   - from DecNN, mechanistic interpretability, probe-based analysis

But combining them would still produce a hybrid system unless state were deliberately kept *inside* the model rather than mirrored into explicit stores and schemas.

## Strongest Conclusion

The research frontier closest to the projection concept is **not** generative UI. It is the intersection of:

- world models
- persistent agent memory
- latent-state interpretability
- stateful inference/runtime design

Generative UI and agentic UI protocols are better understood as **transport and rendering layers** around agents, not as the core conceptual breakthrough.

The gap between current work and the projection concept is:

- Current work: "the model chooses or generates parts of the app"
- Projection concept: "the model's internal state is the app"

That is a materially different ontology.

## Research Thesis Candidates

Based on the survey, the most defensible formulations are:

### Thesis 1

Projection-based applications are a new software category distinct from codegen, agentic UI, and generative UI, because they relocate application semantics from explicit code/schema layers into persistent neural state.

### Thesis 2

The nearest academic ancestors are latent world models and neural program induction, not frontend generation systems.

### Thesis 3

The main blockers are not model capability alone; they are runtime architecture problems:

- persistence
- observability
- concurrency
- determinism
- security
- projection design

## Source Index

- Karpathy, Software 2.0: https://karpathy.medium.com/software-2-0-a64152b37c35
- RobustFill: https://www.microsoft.com/en-us/research/publication/robustfill-neural-program-learning-noisy-io/
- Neural Program Lattices: https://www.microsoft.com/en-us/research/publication/neural-program-lattices/
- Program Synthesis with LLMs: https://huggingface.co/papers/2108.07732
- Thinking Like Transformers / RASP: https://arxiv.org/pdf/2106.06981
- Decodable Neural Networks: https://arxiv.org/pdf/2106.00769
- From Word Models to World Models: https://huggingface.co/papers/2306.12672
- LLMs to construct world models for planning: https://icml.cc/virtual/2023/27213
- MemGPT: https://arxiv.org/abs/2310.08560
- Generative Agents: https://huggingface.co/papers/2304.03442
- StateFlow: https://huggingface.co/papers/2403.11322
- Neural State Machine: https://papers.nips.cc/paper_files/paper/2019/hash/c20a7ce2a627ba838cfbff082db35197-Abstract.html
- World Models: https://huggingface.co/papers/1803.10122
- Dreamer: https://huggingface.co/papers/1912.01603
- Physics of Language Models Part 1: https://arxiv.org/pdf/2305.13673
- Extracting Reduced Logic Programs from Neural Networks: https://jens-lehmann.org/files/2008/ann_extraction.pdf
- Web World Models: https://liner.com/review/web-world-models
- Computer-Using World Model: https://huggingface.co/papers/2602.17365
- CopilotKit generative-ui repo: https://github.com/CopilotKit/generative-ui
- Tambo: https://tambo.co/
- Thesys C1: https://docs.thesys.dev/guides/how-c1-works
- CopilotKit: https://www.copilotkit.ai/
- AG-UI: https://docs.ag-ui.com/introduction
- A2UI: https://a2ui.org/
- MCP Apps official post: https://blog.modelcontextprotocol.io/posts/2026-01-26-mcp-apps/
- MCP Apps overview: https://www.mcp-framework.com/docs/apps/overview
- Letta: https://www.letta.com/
- Letta memory docs: https://docs.letta.com/guides/agents/memory
- Letta core concepts: https://docs.letta.com/core-concepts
- Wordware: https://www.wordware.ai/
- Agentplace: https://qa.agentplace.io/
- World Labs: https://www.worldlabs.ai/
- AMI Labs reporting: https://techcrunch.com/2026/01/23/whos-behind-ami-labs-yann-lecuns-world-model-startup/
- Transient AI: https://transient.ai/
- State Machine of Thoughts: https://papers.cool/arxiv/2312.17445
