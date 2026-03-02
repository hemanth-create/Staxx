# LLM Intelligence Dashboard: Constructive Redesign

---

## Part 1: Repositioning — The Chosen Wedge

### The Wedge: Production Cost Efficiency Intelligence

The product you should build is not a pre-deployment model explorer. It is a **production intelligence layer that answers one question with statistical rigor**:

> *"For each use case in your production system, which model gives equivalent quality at lower cost — and how confident are we?"*

This is the "LLM CFO" wedge. Not a benchmark dashboard. Not a general recommender. A specific, ROI-quantifiable tool that tells engineering teams: **"You are overpaying by $X/month with Y% confidence, and here is the exact switch to make."**

### Why This Wedge, Specifically

**The problem is real and unsolved at scale.** Organizations run GPT-4o on tasks that Claude Haiku handles equally well. They do this because they have no production evidence to justify a switch — only generic benchmarks that don't reflect their prompts, their data, or their quality thresholds. The cost delta is 10–40x across model tiers. Every engineering team with significant LLM spend has this problem.

**The ROI story is concrete and immediate.** "This dashboard costs $500/month and identified $12,000/month in overspend" is a conversation that closes procurement. "This dashboard helps you pick better models" does not close procurement.

**You avoid every major competitor:**

| Competitor | Their Wedge | Why You Don't Compete |
|---|---|---|
| Promptfoo | Pre-deployment evaluation | You're post-deployment, production-data-driven |
| Braintrust | Evaluation datasets + tracking | You don't require gold datasets |
| Langfuse | Observability and tracing | You make recommendations, not just observations |
| Helicone | Cost logging and caching | You do shadow evaluation and statistical swap analysis |
| LMSYS Arena | Human preference benchmarks | You use the customer's own traffic, not generic prompts |
| Martian/Unify | Runtime routing proxy | You recommend, not auto-route — lower risk, higher trust |

**The critical differentiator:** Every competitor uses generic benchmarks or requires ground truth datasets. You use **the customer's actual production prompts** to evaluate alternatives. This is the only evaluation that actually predicts production behavior.

### Revised Product Positioning

```
FROM: "LLM Decision Intelligence Layer"
  → too broad, tool-shaped, no clear buyer

TO: "LLM Cost Efficiency Intelligence"
  → "Find your cheapest model that doesn't degrade quality,
     backed by statistical evidence from your own production traffic."
```

**Primary buyer:** Engineering leaders and platform teams with >$5K/month LLM spend.  
**Secondary buyer:** ML/AI teams who need defensible model selection decisions.  
**Sales motion:** Bottom-up through SDK install, top-down through cost savings story.

---

## Part 2: MVP Redefinition

### The Smallest Statistically Credible Version

The MVP must produce one artifact that is **actionable and defensible**: a ranked list of model alternatives per task category, with confidence intervals, derived from the customer's own production traffic.

Everything else is cut.

**What the MVP does:**

1. Intercepts LLM calls via SDK or proxy
2. Logs production traffic: model version, prompt hash, token counts, latency, cost
3. Classifies calls by task type (automatic, NLP-based)
4. Runs async shadow evaluations: same prompts → cheaper candidate models → N=20 minimum runs
5. Produces swap recommendations: "Switch [task type] from GPT-4o to Claude Haiku: saves $X/month, quality deviation below threshold at 94% confidence"

**What is cut from MVP, no exceptions:**

| Cut Component | Reason |
|---|---|
| Architecture Suggestion Engine | No decision model defined |
| LLM-as-judge scoring | Circular bias, adds cost, no validity without calibration |
| Semantic similarity | Requires ground truth, sentence transformers, labeled data |
| Fine-tune scoring | Phase 2 at earliest |
| Model Explorer / comparison UI | Metadata browser, not differentiated |
| Radar charts | Vanity visualization, misleading with weak data |
| Bedrock, HuggingFace, Local adapters | OpenAI + Anthropic only for MVP |
| Generic recommendation endpoint | Replace with task-specific swap recommendations only |
| User-submitted one-off evaluations | Not the product — this is the Promptfoo use case |

**What must be built correctly from day one — no shortcuts:**

1. **Async evaluation pipeline.** No synchronous eval calls. Every evaluation is a queued job.
2. **Model versioning in registry.** `gpt-4o-2024-08-06` is not `gpt-4o`. Every evaluation links to a specific model version ID, never a display name.
3. **N≥20 enforcement.** Results with fewer than 20 runs are marked "Insufficient Data" and excluded from recommendations.
4. **Variance tracking.** Standard deviation is stored alongside mean for every metric. High-variance results are flagged before any recommendation is made.
5. **Immutable audit log.** Every recommendation made, every evaluation run, append-only. This is your enterprise differentiator from day one.
6. **Proper cost model.** Task-aware input/output token ratio. Summarization is 80% input tokens. Classification is 90% input tokens. These ratios change cost rankings dramatically.

---

## Part 3: Scoring Engine Redesign

### The Statistical Framework

Replace the weighted linear sum entirely. Here is the replacement, step by step.

**Step 0: Data Collection Requirements**

Before any score is computed, enforce:

```python
class EvaluationRequirements:
    MIN_RUNS = 20                    # Minimum runs per (model_version, task_type)
    MAX_CV = 0.25                    # Max coefficient of variation (σ/mean)
    MIN_COST_SAMPLES = 100           # Production calls to establish cost baseline
    DRIFT_WINDOW_DAYS = 14           # Recompute if model not evaluated in 14 days
    
    def is_eligible(self, agg: AggregatedMetrics) -> tuple[bool, str]:
        if agg.n < self.MIN_RUNS:
            return False, f"Insufficient data: {agg.n} runs (need {self.MIN_RUNS})"
        if agg.latency_cv > self.MAX_CV:
            return False, f"High variance: CV={agg.latency_cv:.2f} (threshold {self.MAX_CV})"
        if agg.last_evaluated_days > self.DRIFT_WINDOW_DAYS:
            return False, f"Stale: last evaluated {agg.last_evaluated_days}d ago"
        return True, "eligible"
```

Never let scores from ineligible evaluations reach the ranking stage.

**Step 1: Per-Metric Normalization**

Normalize independently per task category. Normalization range must be computed across only the models being compared, recomputed each time the model set changes:

```python
def normalize_min_max(values: dict[str, float], higher_is_better: bool) -> dict[str, float]:
    """
    Normalize to [0, 1] where 1 is always best.
    For cost/latency (lower=better): flip after normalization.
    """
    mn, mx = min(values.values()), max(values.values())
    if mx == mn:
        return {k: 1.0 for k in values}  # All equal → all score 1.0
    
    normalized = {k: (v - mn) / (mx - mn) for k, v in values.items()}
    
    if not higher_is_better:
        normalized = {k: 1.0 - v for k, v in normalized.items()}
    
    return normalized

# Apply separately per metric
cost_scores    = normalize_min_max(cost_per_task,    higher_is_better=False)
latency_scores = normalize_min_max(p95_latency,      higher_is_better=False)
json_scores    = normalize_min_max(json_validity_rate, higher_is_better=True)
```

**Step 2: Confidence Interval Propagation**

Every normalized score carries an uncertainty range derived from evaluation variance. This is non-negotiable. A score without a confidence interval is not a score — it is a guess.

```python
from dataclasses import dataclass
import numpy as np
from scipy import stats

@dataclass
class ScoredMetric:
    point_estimate: float
    ci_lower: float
    ci_upper: float
    n: int
    
    @classmethod
    def from_runs(cls, values: list[float], confidence: float = 0.95) -> "ScoredMetric":
        n = len(values)
        mean = np.mean(values)
        se = stats.sem(values)  # Standard error of the mean
        ci = stats.t.interval(confidence, df=n-1, loc=mean, scale=se)
        return cls(
            point_estimate=mean,
            ci_lower=ci[0],
            ci_upper=ci[1],
            n=n
        )
    
    @property
    def is_significantly_different_from(self, other: "ScoredMetric") -> bool:
        """
        Two models are NOT significantly different if their CIs overlap.
        Prevent misleading rankings when differences are within noise.
        """
        return self.ci_lower > other.ci_upper or other.ci_lower > self.ci_upper
```

**Step 3: Pareto Frontier Before Ranking**

Identify dominated models before any weighted comparison. Never rank-order models on a single composite score without first showing the Pareto frontier.

```python
def compute_pareto_frontier(
    models: list[str],
    metrics: dict[str, dict[str, float]]  # {model: {metric: score}}
) -> tuple[list[str], list[str]]:
    """
    Returns (pareto_optimal, dominated).
    A model is dominated if another model is >= on all metrics and > on at least one.
    """
    dominated = set()
    
    for candidate in models:
        for challenger in models:
            if candidate == challenger:
                continue
            candidate_scores = metrics[candidate]
            challenger_scores = metrics[challenger]
            
            at_least_as_good = all(
                challenger_scores[m] >= candidate_scores[m]
                for m in candidate_scores
            )
            strictly_better_on_one = any(
                challenger_scores[m] > candidate_scores[m]
                for m in candidate_scores
            )
            
            if at_least_as_good and strictly_better_on_one:
                dominated.add(candidate)
                break
    
    pareto_optimal = [m for m in models if m not in dominated]
    return pareto_optimal, list(dominated)
```

**Step 4: TOPSIS Within the Pareto Set**

Only apply weighted scoring to the Pareto-optimal set. This prevents weights from artificially rescuing a dominated model.

```python
def topsis(
    models: list[str],
    normalized_scores: dict[str, dict[str, float]],  # already [0,1], higher=better
    weights: dict[str, float]
) -> dict[str, float]:
    """
    TOPSIS: Technique for Order of Preference by Similarity to Ideal Solution.
    Returns relative closeness score [0,1] for each model.
    """
    metrics = list(weights.keys())
    W = np.array([weights[m] for m in metrics])
    
    # Build weighted normalized matrix
    matrix = np.array([
        [normalized_scores[model][m] * W[i] for i, m in enumerate(metrics)]
        for model in models
    ])
    
    # Ideal best and worst (since all normalized to higher=better)
    ideal_best  = matrix.max(axis=0)
    ideal_worst = matrix.min(axis=0)
    
    # Euclidean distance from ideal and anti-ideal
    d_best  = np.sqrt(((matrix - ideal_best) ** 2).sum(axis=1))
    d_worst = np.sqrt(((matrix - ideal_worst) ** 2).sum(axis=1))
    
    # Relative closeness (1 = closest to ideal, 0 = farthest)
    closeness = d_worst / (d_best + d_worst)
    
    return {model: float(closeness[i]) for i, model in enumerate(models)}
```

**Step 5: Overlap-Aware Ranking**

Final rankings must communicate when differences are statistically insignificant:

```python
def rank_with_significance(
    topsis_scores: dict[str, float],
    ci_bounds: dict[str, tuple[float, float]]
) -> list[RankedModel]:
    sorted_models = sorted(topsis_scores, key=topsis_scores.get, reverse=True)
    ranked = []
    
    for i, model in enumerate(sorted_models):
        lower, upper = ci_bounds[model]
        
        # Check if previous model's CI overlaps
        effectively_tied_with_above = (
            i > 0 and
            lower < ci_bounds[sorted_models[i-1]][1]
        )
        
        ranked.append(RankedModel(
            model=model,
            rank=i + 1,
            topsis_score=topsis_scores[model],
            ci_lower=lower,
            ci_upper=upper,
            effectively_tied=effectively_tied_with_above,
            recommendation_text=(
                f"Statistically equivalent to #{i} — verify with more runs"
                if effectively_tied_with_above else None
            )
        ))
    
    return ranked
```

### What This Scoring System Gives You

- No model can appear in a ranking without N≥20 runs
- No recommendation is made when CI overlap indicates statistical ties
- Dominated models are filtered before weights are applied
- Cost is always task-aware (input/output ratio per task category)
- Every score the UI shows has a visible confidence interval
- Users adjusting weights operate on the Pareto-optimal set only — they cannot resurrect dominated models

---

## Part 4: Evaluation Validity Without Gold Datasets

### The Honest Assessment

Do not attempt quality scoring in MVP. Here is why and what to do instead.

**The fundamental problem:** Without ground truth, every quality metric is measuring something other than quality. Fluency is not quality. LLM-as-judge is not quality. Semantic similarity to a reference (which model's output do you use as reference?) is not quality. These proxies each introduce bias that is difficult to quantify and impossible to explain to a skeptical engineering team.

**What you can measure validly without gold datasets:**

| Metric | How to Measure | Statistical Validity |
|---|---|---|
| Cost per task | Actual token counts × price | Exact — no approximation |
| Latency p50/p95/p99 | Wall-clock timing per call | Exact — just measure it |
| JSON schema validity | Validate against schema | Binary, deterministic |
| Output length consistency | Token count variance | Objective measurement |
| Error rate | API errors, malformed outputs | Objective measurement |
| Instruction adherence (structured) | Regex/schema validation on constrained outputs | Objective for constrained tasks |

**For tasks where output is objectively evaluable (classification, extraction, JSON generation):**
Quality is not ambiguous. Either the output is valid or it is not. Start here. These are the use cases where your tool provides the highest value with zero ground-truth requirement.

**For tasks where output is subjective (summarization, open-ended generation):**
Do not score quality in MVP. Sell on cost and latency only. Position this honestly: *"For generation tasks, we track cost and latency. Quality requires your team's evaluation criteria."* This is more trustworthy than a fake quality score.

**The minimum-bias quality approach when you must go beyond MVP:**

```
Approach: Consistency as a Proxy for Reliability
─────────────────────────────────────────────────
1. Run the same prompt N=20 times per model
2. Compute pairwise semantic similarity across all N outputs
3. High mean similarity + low variance → consistent model
4. Low mean similarity → unreliable / high-entropy model

This measures reliability, not quality.
Present it as: "Output consistency score" not "Quality score"
This is valid without ground truth and directly useful for production decisions.
```

**The relative-reference approach (Phase 2 only):**

When a customer has a current production model, that model's outputs become the reference:

```
For each prompt P:
  reference_output = current_production_model(P)
  candidate_output = cheaper_model(P)
  
  similarity = semantic_similarity(reference_output, candidate_output)
  structure_match = schema_valid(candidate_output) == schema_valid(reference_output)
  
  recommendation: "Cheaper model produces outputs {X}% similar to your current model"
```

This never claims to measure absolute quality. It measures deviation from current behavior, which is exactly what an engineering team needs to justify a model switch to stakeholders.

---

## Part 5: Clean Architecture

```
╔══════════════════════════════════════════════════════════════════════╗
║                    PRODUCTION APPLICATIONS                          ║
║              (Customer's existing LLM-calling services)             ║
╚══════════════════════╤═══════════════════════════════════════════════╝
                       │  
         ┌─────────────▼──────────────────────┐
         │         CAPTURE LAYER              │
         │                                    │
         │  ┌────────────┐  ┌──────────────┐ │
         │  │ Python SDK │  │ Node.js SDK  │ │  ← drop-in wrappers
         │  └────────────┘  └──────────────┘ │    around openai/anthropic
         │  ┌────────────────────────────┐   │    client libraries
         │  │  HTTP Proxy (sidecar mode) │   │
         │  └────────────────────────────┘   │
         │                                    │
         │  Captured per call:                │
         │  model_version_id, prompt_hash,    │
         │  input_tokens, output_tokens,      │
         │  latency_ms, raw_output_ref,       │
         │  task_tag, session_id, error       │
         └─────────────────┬──────────────────┘
                           │ async publish
         ┌─────────────────▼──────────────────┐
         │          MESSAGE QUEUE             │
         │         (Redis Streams)            │
         │                                    │
         │  stream:raw_calls                  │
         │  stream:eval_jobs                  │
         │  stream:drift_checks               │
         └───┬──────────────────────┬─────────┘
             │                      │
┌────────────▼──────────┐  ┌───────▼────────────────────────────────┐
│   METRICS WORKER      │  │        SHADOW EVAL WORKER              │
│   (Celery, N workers) │  │        (Celery, separate queue)        │
│                       │  │                                        │
│ - Cost calculation    │  │ - Receives (prompt, task_type)         │
│   (task-aware I/O     │  │ - Fans out to candidate model adapters │
│    token ratios)      │  │ - Enforces N=20 minimum runs           │
│ - p50/p95/p99 latency │  │ - Rate limit manager per provider      │
│ - JSON validity check │  │ - Captures same metrics as above       │
│ - Task auto-classify  │  │ - Runs statistical significance test   │
│ - Variance tracking   │  │ - Writes to eval_runs, flags if N<20  │
│ - Canary drift check  │  │                                        │
│   (scheduled, 6h)     │  │  ┌──────────────────────────────────┐ │
└────────────┬──────────┘  │  │    RATE LIMIT MANAGER            │ │
             │             │  │   per-provider token buckets     │ │
             │             │  │   exponential backoff + jitter   │ │
             │             │  │   stored in Redis                │ │
             │             │  └──────────────────────────────────┘ │
             │             └───────────────────┬────────────────────┘
             │                                 │
┌────────────▼─────────────────────────────────▼────────────────────┐
│                         STORAGE LAYER                             │
│                                                                   │
│  ┌──────────────────────────┐    ┌──────────────────────────────┐ │
│  │       PostgreSQL         │    │        S3 / MinIO            │ │
│  │                          │    │                              │ │
│  │  model_versions          │    │  raw_outputs/               │ │
│  │  ├─ id (uuid)            │    │  ├─ {eval_run_id}.json       │ │
│  │  ├─ provider_model_id    │    │  │   (content-addressed)    │ │
│  │  ├─ capabilities (jsonb) │    │  │                          │ │
│  │  ├─ pricing (jsonb)      │    │  eval_datasets/             │ │
│  │  ├─ valid_from           │    │  ├─ {task_type}/            │ │
│  │  └─ valid_until          │    │  │   representative prompts │ │
│  │                          │    │  │                          │ │
│  │  eval_runs               │    │  audit_log/                 │ │
│  │  ├─ id                   │    │  └─ immutable append-only   │ │
│  │  ├─ model_version_id (→) │    │      (WORM if enterprise)   │ │
│  │  ├─ task_type            │    └──────────────────────────────┘ │
│  │  ├─ prompt_hash          │                                   │
│  │  ├─ input_tokens         │    ┌──────────────────────────────┐ │
│  │  ├─ output_tokens        │    │           Redis              │ │
│  │  ├─ latency_ms           │    │                              │ │
│  │  ├─ cost_usd             │    │  rate_limit:{provider}       │ │
│  │  ├─ json_valid           │    │  score_cache:{model}:{task}  │ │
│  │  ├─ output_ref (→ S3)    │    │  leaderboard:{task_type}     │ │
│  │  ├─ n_run                │    │  session:{token}             │ │
│  │  └─ created_at           │    └──────────────────────────────┘ │
│  │                          │                                   │
│  │  production_calls (hyper)│    ┌──────────────────────────────┐ │
│  │  ├─ model_version_id     │    │  TimescaleDB (or pg+ext)     │ │
│  │  ├─ task_type            │    │                              │ │
│  │  ├─ cost_usd             │    │  cost_history (time-series)  │ │
│  │  ├─ latency_ms           │    │  latency_history             │ │
│  │  └─ ts (timestamptz)     │    │  drift_signals               │ │
│  └──────────────────────────┘    └──────────────────────────────┘ │
└─────────────────────────────────────────────┬─────────────────────┘
                                              │
┌─────────────────────────────────────────────▼─────────────────────┐
│                      SCORING ENGINE v2                            │
│                                                                   │
│   Input: aggregated metrics by (model_version, task_type)        │
│                                                                   │
│   ① Eligibility gate  →  N<20 or stale: excluded, not scored    │
│   ② CV gate           →  σ/mean > 0.25: flagged, not ranked     │
│   ③ Min-max normalize →  per metric, per current model set       │
│   ④ Pareto frontier   →  identify dominated models              │
│   ⑤ TOPSIS            →  rank Pareto-optimal set with weights   │
│   ⑥ CI propagation    →  flag statistically tied rankings       │
│   ⑦ Output            →  ranked list + CI + Pareto chart data   │
│                           + "insufficient data" list             │
│                           + "high variance" warnings             │
└─────────────────────────────────────────────┬─────────────────────┘
                                              │
┌─────────────────────────────────────────────▼─────────────────────┐
│                       API LAYER (FastAPI)                         │
│                                                                   │
│   Middleware:  JWT + optional SAML | RBAC | Audit every call     │
│                                                                   │
│   POST /capture/calls          Ingest production call logs       │
│   POST /evaluate/shadow        Queue shadow evaluation job       │
│   GET  /evaluate/{job_id}      Poll job status + stream results  │
│   GET  /recommend/{task_type}  Ranked swap recommendations       │
│   GET  /costs/breakdown        Cost by model, task, time range   │
│   GET  /costs/savings          Projected savings from swaps      │
│   GET  /models/registry        Model versions with capabilities  │
│   GET  /alerts/drift           Drift signals + canary results    │
│   GET  /scores/{task_type}     Full score report with CIs        │
└─────────────────────────────────────────────┬─────────────────────┘
                                              │
┌─────────────────────────────────────────────▼─────────────────────┐
│                       DASHBOARD (React)                           │
│                                                                   │
│   Cost Intelligence       Swap Recommendations (with CI bars)    │
│   Latency Percentiles     Evaluation Job Status                  │
│   Model Drift Alerts      Task-Type Breakdown                    │
│   Pareto Chart            Insufficient Data Warnings             │
└───────────────────────────────────────────────────────────────────┘
```

### What This Architecture Removes vs Your Original

| Removed | Replaced With |
|---|---|
| Synchronous evaluation endpoint | Async job queue with SSE polling |
| Postgres for raw outputs | S3/MinIO with reference IDs in Postgres |
| Generic cost_history table | TimescaleDB hypertable (time-series native) |
| Architecture Suggestion Engine | Nothing — cut permanently |
| LLM-as-judge | Consistency scoring (Phase 2, clearly labeled) |
| model_capabilities (flat) | model_versions (append-only, versioned) |
| User-adjustable weights on full model set | User weights apply only to Pareto set |

---

## Part 6: Execution Roadmap

### Phase 1: Foundation (Weeks 1–6)

**Goal:** Production traffic capture + cost/latency reporting. Statistically valid. No quality scoring.

**Week 1–2: Core Data Infrastructure**
- Postgres schema: `model_versions`, `eval_runs`, `production_calls`
- TimescaleDB extension for `production_calls` (time-series queries on this table are your primary read pattern)
- S3/MinIO setup with lifecycle policy (raw outputs expire after 90 days by default)
- Redis for rate limiting and session management
- Celery + Redis Streams for job queue

**Week 3–4: Capture Layer + Adapters**
- Python SDK: thin wrapper over `openai` and `anthropic` clients. Zero behavior change. One import swap.
- HTTP Proxy mode: for non-Python environments
- OpenAI adapter + Anthropic adapter only
- Token counting per provider (tiktoken for OpenAI, Anthropic tokenizer for Claude)
- Task auto-classifier: lightweight model (fine-tuned distilbert or rule-based heuristic) to tag calls as summarization / extraction / classification / generation / code

**Week 5: Metrics Worker**
- Cost calculation with task-aware I/O token ratios (hardcoded per task type initially)
- p50/p95/p99 latency aggregation by `(model_version, task_type, day)`
- JSON validity check (attempt `json.loads()`, validate against schema if provided)
- Write aggregated metrics to Postgres on a 5-minute schedule

**Week 6: API + Basic Dashboard**
- `/costs/breakdown` and `/costs/savings` endpoints
- Basic React dashboard: cost by model and task type, latency percentiles
- No recommendations yet — just visibility

**Phase 1 Engineering Risks:**
- Token counting accuracy: test against actual provider billing, not estimates
- Task classification false positives: misclassified tasks corrupt per-category scores — validate with real traffic samples
- Proxy latency overhead: must add <5ms to every production call or customers won't instrument it

---

### Phase 2: Shadow Evaluation + Recommendations (Weeks 7–14)

**Goal:** First statistically valid swap recommendations.

**Week 7–9: Shadow Eval Pipeline**
- Shadow eval worker: receives `(prompt_hash, prompt_content, task_type)`, fans out to N=2 candidate models
- Rate limit manager: per-provider token bucket in Redis, exponential backoff
- N=20 enforcement: job stays open until minimum runs complete
- Variance tracking: compute CV after each run, flag jobs exceeding threshold
- Store results in `eval_runs`, output references in S3

**Week 10–11: Scoring Engine v2**
- Eligibility gate implementation
- Min-max normalization per `(task_type, current model set)`
- Pareto frontier computation
- TOPSIS implementation — unit test this thoroughly with known inputs
- Confidence interval propagation

**Week 12–13: Recommendation Engine**
- `/recommend/{task_type}` endpoint
- Recommendation format: "Switch X% of [task_type] calls from [current model] to [candidate]: saves $Y/month. Quality deviation: {consistency score}. Statistical confidence: {CI}."
- Explicitly label cost-only vs quality-including recommendations
- `/costs/savings` expanded with projected savings per recommendation

**Week 14: Model Drift Detection**
- Canary evaluation suite: 20 representative prompts per task type, sampled from production traffic
- Scheduled job: run canary suite every 6 hours per active model version
- Drift signal: if p95 latency or cost changes >15% or JSON validity drops >5pp, emit alert
- `/alerts/drift` endpoint + email notification

**Phase 2 Engineering Risks:**
- Shadow eval spend: sending 20 runs of every new prompt to 2 models costs real money — implement prompt deduplication (cache by hash) and sampling (evaluate 10% of production traffic, not 100%)
- Canary suite maintenance: representative prompts become stale as production traffic evolves — rebuild canary suite monthly

---

### Phase 3: Enterprise + Quality (Weeks 15–26)

**Goal:** Enterprise readiness + optional quality scoring for structured tasks.

**Weeks 15–18: Enterprise Features**
- RBAC: viewer / analyst / admin roles per workspace
- SAML/SSO integration
- Immutable audit log (S3 WORM bucket, append-only Postgres partition)
- Budget governance: per-team monthly spend caps, Slack/email alerts at 80% threshold
- Cost allocation: tag calls by team, product, feature via SDK metadata

**Weeks 19–22: Quality Scoring (Structured Tasks Only)**
- Schema validation scoring: for extraction and classification tasks, validate outputs against customer-provided JSON schema
- Instruction adherence scoring: regex + structured output rules, no LLM-as-judge
- Consistency scoring: pairwise similarity across N runs (using sentence-transformers, self-hosted)
- Add quality dimension to TOPSIS for tasks where it is objectively measurable
- Never add quality scoring for open-ended generation without customer-provided ground truth

**Weeks 23–26: Integrations + API**
- Datadog integration: push cost and drift metrics to customer dashboards
- PagerDuty: drift alerts as incidents
- Public REST API with API keys for programmatic access
- Webhook support for recommendations and drift alerts
- Terraform provider (stretch goal) for infrastructure-as-code model registry management

---

### Required Infrastructure (By Phase)

| Component | Phase 1 | Phase 2 | Phase 3 |
|---|---|---|---|
| Postgres | Required | Required | Required |
| TimescaleDB extension | Required | Required | Required |
| Redis | Required | Required | Required |
| Celery | Required | Required | Required |
| S3/MinIO | Required | Required | WORM for audit |
| Sentence Transformers | Not needed | Not needed | Self-hosted |
| SAML provider | Not needed | Not needed | Required |

Hosting recommendation: Railway or Render for Phase 1. AWS ECS with RDS + ElastiCache for Phase 2+. Do not Kubernetes until you have paying customers.

---

## Part 7: Final Recommendation

### Should You Build This?

**Yes, but only in the repositioned form.**

The original design would produce a well-engineered demo that competes with free tools and loses. The repositioned design — production cost efficiency intelligence with statistically valid swap recommendations — solves a problem that is real, growing, and poorly addressed by existing tools.

**The exact form to pursue:**

Build a Python SDK (primary) + HTTP proxy (secondary) that instruments existing LLM calls with zero behavior change. The onboarding story is: `pip install llm-intel`, swap your client initialization, see your cost breakdown in 10 minutes. No prompt templates to write, no golden datasets to label, no benchmarks to run. Just instrument your existing code and get immediate visibility.

The wedge is cost visibility → the upsell is swap recommendations → the enterprise story is governance and audit.

**The three things that will determine whether this succeeds:**

1. **SDK instrumentation must be genuinely zero-friction.** If it requires code changes beyond a single import, adoption will stall. The instrumentation story is the go-to-market story.

2. **Recommendations must be conservative and falsifiable.** Do not recommend a model switch until you have N≥20 runs and the CI excludes quality regression at 95% confidence. One bad recommendation that degrades a customer's production system will destroy trust faster than any competitor. Be the tool that says "we don't have enough data yet" rather than the tool that confidently recommends the wrong thing.

3. **The cost savings number must be visible and compelling on day one.** The first screen a user sees after instrumentation should show: "In the last 7 days, you spent $X on LLM calls. We've identified $Y in potential savings. Evaluations are running." That number is your retention driver, your upsell trigger, and your sales collateral.

**The adjacent opportunity if you determine the SDK distribution problem is too hard:**

A self-hostable evaluation platform for regulated industries — specifically healthcare and financial services — where teams cannot send prompts to third-party services (Braintrust, Langfuse are SaaS-only). Open source core, enterprise license for compliance features (HIPAA audit logs, data residency controls, RBAC). This is a harder technical product but the distribution is clearer: open source drives trial, compliance requirements drive conversion. Braintrust does not compete here. Langfuse is moving into this space but is not yet enterprise-compliant.

Either path is defensible. The SDK path has faster time-to-value and better bottom-up distribution. The self-hosted evaluation path has a clearer enterprise buyer and higher contract values. Choose based on your network: if you have relationships with engineering teams at companies with meaningful LLM spend, build the SDK. If you have relationships in regulated industries, build the self-hosted evaluation platform.