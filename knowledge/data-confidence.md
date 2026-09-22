# Data Confidence Rubric

> Copied from AK-Threads-Booster. threads-bench uses only the level labels (Directional / Weak / Usable / Strong / Deep) and the honest-degrade rules. For public benchmark data the ceiling is `Usable`; see SKILL.md Step 3.

---

## Why this exists

Fans run this skill from day one, often with very little data. Without a shared rubric, different skills used different thresholds and told the user different things about the same dataset. This file is the single source of truth.

All skills must classify the available data using the levels below and carry the label into the output. Do not skip this step.

---

## Levels

The level is determined by the count of **comparable posts** — historical posts that match the current task on at least 2 of: content type, hook type, topic cluster, word-count band.

| Level | Comparable posts | Meaning | What you may say |
|-------|-----------------|---------|-----------------|
| **Directional** | < 5 | Not enough data for stable conclusions. Observations are one-off, not patterns. | "For your reference, but sample is too small to call a pattern." |
| **Weak** | 5–9 | Enough to notice a tendency, not enough to treat as evidence. | "There is a lean toward X, but confidence is low." |
| **Usable** | 10–19 | Stable enough to guide decisions, still sensitive to outliers. | "Based on your history, X tends to outperform Y, for your reference." |
| **Strong** | 20–49 | Reliable working baseline. | "Your data consistently shows X." |
| **Deep** | 50+ | Cross-analysis becomes meaningful (e.g., hook × topic × time). | "You can trust multi-dimensional splits here." |

---

## How to surface this in output

Every skill that produces analysis must include a `Reference Strength` section (or equivalent) at the end with:

- Data path used (full tracker / tracker-only fallback / temporary paste-in)
- Total posts in tracker
- Comparable posts used for this task
- Level label (Directional / Weak / Usable / Strong / Deep)
- Which specific claims are strong vs weak

Example:

```text
### Reference Strength
- Data path: full tracker (tracker + style_guide + brand_voice)
- Posts in tracker: 34
- Comparable posts used: 8
- Level: Weak
- Strong claims: hook type outperforms question hooks in your history
- Weak claims: word-count band recommendation (only 3 posts in range)
```

---

## Honest-degrade rules

When data is thin:

1. Do not substitute generic platform benchmarks without saying so.
2. Do not present weak conclusions as strong. Use the label.
3. When a specific comparison set is too small, state which set failed and why, then continue with the sets that did meet threshold.
4. If the user paste-in is the only data source, label the entire analysis `Temporary — not persisted`.

The user can still make good decisions with a Weak or Directional label. They cannot make good decisions if you pretended Weak was Strong.
