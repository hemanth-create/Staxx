Phase 1: Prime the LLM with project context
Paste this once at the start of every new conversation:
Read the following architecture document carefully. This is the full 
system design for "Staxx Intelligence" — an LLM cost optimization 
SaaS platform. Do NOT generate any code yet. Just confirm you 
understand the system by summarizing:

1. What Staxx does in one sentence
2. The 4 architectural layers
3. How data flows from integration to dashboard

Once you confirm understanding, I'll tell you which component to build.

---
[PASTE ONLY SECTIONS 1-6 OF THE MD FILE HERE — the architecture part, 
NOT the prompts]
---
This gives the LLM the full picture without overwhelming it with build instructions. Wait for it to confirm understanding before moving on.
Phase 2: Feed the specific build prompt
Once it confirms, send this:
Good. Now build the following component. Read every requirement 
carefully — I need production-ready code, not prototypes. Follow 
the file structure exactly as specified. Every file must be complete 
and runnable.

If any requirement is ambiguous, state your assumption before coding.

Do not skip files. Do not use placeholder comments like 
"# implement later". Every function must be fully implemented.

---
[PASTE THE SPECIFIC PROMPT — e.g., Prompt 1: Proxy Gateway]
---
The critical phrases here are "production-ready, not prototypes", "do not skip files", and "state your assumption." Without these, LLMs default to lazy scaffolding.
Phase 3: Review and iterate
After it generates code, follow up with:
Now review the code you just generated against these criteria:

1. Are all files from the file structure present and complete?
2. Are there any functions with placeholder/TODO comments?
3. Are all imports valid and all dependencies listed in requirements.txt?
4. Does the error handling cover edge cases mentioned in the requirements?
5. Are type hints present on every function?

List any gaps, then fix them.
This self-review step catches 80% of the shortcuts LLMs take on first pass.