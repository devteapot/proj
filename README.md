# proj

**The neural app runtime.** Applications where the user interface is a real-time projection of the model's internal state — the neural network *is* the application.

## The Core Idea

Software 1.0: Code defines behavior. You write text files → the program executes → the user interacts with a UI built from that code.

**Software 2.0 (Karpathy, 2017):** The program lives in neural network weights. You can't read the code by inspecting the files — it's millions of floating-point numbers.

**proj (this project):** The neural network *is* the application. It holds the state, the logic, the data model, the behavior. The UI is not built from code — it's **rendered from the model's internal state in real-time**. There is no code layer between the user and the app. The model is both the backend and the state machine. The interface is a projection — a rendering of what the network has internalized.

```
Traditional:  User → UI layer → Code layer → Data → Model
proj:         User → Projection layer → Neural network (the app)
```

## Philosophy

- The app **lives in the weights**. Source code is just one possible rendering of what the network knows.
- The UI is a **real-time projection** of the model's current state, not a fixed template or code-generated page.
- The developer **curates the model** (prompt, state, capabilities), not the UI. The model generates the interface from its own understanding.
- **You can outsource thinking but never understanding.** The projection must be inspectable and verifiable.

## Related Work

See `references/` for a detailed survey of related research, existing systems, and academic papers.

## Structure

```
proj/
├── README.md           # You are here
├── references/         # Research survey, papers, existing systems
└── experiments/        # Prototypes and proof-of-concepts
```
