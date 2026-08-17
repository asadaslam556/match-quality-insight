# Match Quality Analysis

Five findings from 6,000 scored applications, 5,496 of which have a recruiter decision.

**The short version.** The platform's two scorers both work, but the headline comparison
between them is wrong. Measured across all job families the LLM scorer looks better
(AUC 0.724 against 0.689). That ranking is an artefact of one broken segment. Remove
Healthcare and the rule scorer is clearly ahead (0.782 against 0.729), and it wins in four
of the five job families. Any decision to lean harder on the LLM, taken on the pooled
number, would be based on a bug.

Beyond that: the LLM scores candidates highest when it knows least about them, the v2
release inflated every score without improving accuracy, Austrian candidates receive a
free bonus, and recruiters have quietly stopped opening the AI panel.

---

## How this was measured

`recruiter_decision` is the outcome variable. `interviewed` and `hired` count as positive,
`rejected` as negative, and the 504 pending applications (8.4%) are excluded rather than
treated as rejections.

The main metric is AUC, the probability that a randomly chosen positive application is
ranked above a randomly chosen negative one. It is the right default here because it
judges ranking quality and is unaffected by where a threshold sits, which matters when one
of the findings below is that a threshold moved. Precision and recall at the live
threshold, and precision@k, are reported alongside it because those are what recruiters
actually experience.

**The ground truth is a proxy and it is not neutral.** Recruiters see both scores before
they decide. So the labels are partly caused by the scores being graded against them, which
inflates both scorers and inflates the better-presented one more. Every AUC below should be
read as an upper bound on real predictive quality. The fix is not analytical, it is a
product change, and it is proposal 5.

---

## Finding 1: the rule scorer is broken for Healthcare, and it is corrupting the platform-level verdict

**Evidence.** Healthcare applications get a mean `rule_score` of 0.141. Every other job
family sits between 0.557 and 0.585. The highest Healthcare score in the entire dataset is
0.305, which is below the 0.5 cut-off for the `medium` bucket. The consequence is
categorical rather than statistical:

| Job family | Applications | Mean rule score | Bucketed `low` | Positive rate |
|---|---|---|---|---|
| Healthcare | 1,363 | 0.141 | **100.0%** | 50.8% |
| IT | 796 | 0.557 | 36.7% | 51.7% |
| Logistics | 2,025 | 0.571 | 36.6% | 52.0% |
| Manufacturing | 872 | 0.585 | 31.2% | 53.9% |
| Office & Admin | 944 | 0.576 | 32.6% | 54.3% |

Every one of the 1,363 Healthcare applications is labelled `low fit`. Not one reaches
`medium`. Meanwhile Healthcare candidates convert at 50.8%, statistically indistinguishable
from the 52.8% of everyone else. The candidates are fine. The scorer is not.

Three checks confirm this is a scorer defect and not a property of the data. It holds
uniformly across all 18 Healthcare jobs. It holds in both countries (AT 0.144, DE 0.140).
And *within* Healthcare the rule scorer still ranks well, at AUC 0.702, so the ordering
survives and only the scale is wrong. The ratio between the Healthcare mean and the
all-other-families mean is 4.04, which points at a normalisation step dividing by a
requirement count that the Healthcare rule set does not share.

**Why it matters, and this is the part to take to management.** The compression drags the
rule scorer's pooled AUC down to 0.689 and flips the comparison between the two systems:

| View | Rule scorer | LLM scorer | Better |
|---|---|---|---|
| All job families | 0.689 | 0.724 | LLM |
| Excluding Healthcare | **0.782** | 0.729 | **Rule** |

Per family, the rule scorer wins in four of five (Logistics 0.791 against 0.748,
Office & Admin 0.798 against 0.743, Manufacturing 0.768 against 0.706, IT 0.755 against
0.692) and ties in Healthcare. This is Simpson's paradox: the pooled figure says the
opposite of every segment inside it. It also manufactures fake disagreement between the two
systems. Agreement rises from 65.9% to 74.3% once Healthcare is removed.

The business cost is direct. Rescaling Healthcare by the observed factor would move 772 of
the 1,239 decided Healthcare applications into `medium` or `good`, and that group converts
at 62.6%, well above the 52.3% platform average. The scorer is currently labelling the best
performing group on the platform as uniformly poor.

**Proposal for the rule scorer team.** Fix the normalisation in the Healthcare rule set,
then add a release check that fails if any job family's `rule_fit` distribution contains
zero of any bucket, or if a family's mean score sits more than two standard deviations from
the cross-family mean. This bug produced a mathematically impossible output, so a schema
level assertion would have caught it before any analysis was needed. Until the fix ships,
suppress the `rule_fit` label for Healthcare in the recruiter UI rather than showing all
1,363 applications a `low fit` badge that carries no information.

---

## Finding 2: the LLM scores candidates highest when it knows least about them

**Evidence.** Mean `llm_score` by profile completeness:

| Profile completeness | Applications | Mean LLM score | Positive rate |
|---|---|---|---|
| 0.0 to 0.2 | 323 | 72.5 | |
| 0.2 to 0.3 | 365 | 73.7 | 48.0% (all bands below 0.4) |
| 0.3 to 0.4 | 504 | **74.0** | |
| 0.4 to 0.5 | 644 | **61.7** | |
| 0.5 to 0.7 | 1,638 | 60.4 | 51.0% (0.4 to 0.7) |
| 0.7 to 1.0 | 2,526 | 63.2 | 55.4% |

The relationship is inverted and the break is a cliff, not a gradient: 74.0 immediately
below 0.4, 61.7 immediately above it. Candidates with the least filled-in profiles receive
scores roughly 11.7 points higher than everyone else, and they convert at 48.0% against
53.3%. The scorer is most confident exactly where it has least evidence.

This is not a confound. It holds in every job family (gap between +10.2 and +14.1) and in
both model versions (+12.1 on v1, +11.1 on v2). It is also not a ranking failure: within
the thin-profile group the LLM still achieves AUC 0.746, slightly above its 0.737 on
complete profiles. That distinction is the actionable part. The scorer orders sparse
candidates correctly relative to each other, but places the whole group on the wrong
absolute level. It is a calibration failure, so it is invisible to any within-job ranking
check and only appears when a fixed threshold is applied across candidates.

The likely mechanism is that a sparse profile gives the model nothing to object to. Absent
evidence reads as absence of problems.

**Proposal for the LLM scorer team.** Two changes. First, pass profile completeness into
the prompt explicitly and instruct the model to return a confidence band alongside the
score, then hold back the "strong candidate" flag for low-confidence outputs rather than
letting an uncalibrated 75 trigger it. Second, and testable this sprint, fit a completeness
based recalibration: a simple per-band offset that maps the observed positive rate back
onto the score. Validate it by checking that the calibration curve for the thin band lands
on the curve for complete profiles. As a product side-effect, this turns profile
completeness into something worth prompting candidates to improve, which it currently is
not.

---

## Finding 3: scorer-v2 inflated every score and bought no accuracy with it

**Evidence.** The rollout was a clean cutover with no overlap: v1 from September 2025 to
February 2026, v2 from March 2026 onward.

| | scorer-v1 | scorer-v2 | Change |
|---|---|---|---|
| Mean score | 60.8 | 68.5 | +7.8 |
| Median score | 62 | 69 | +7 |
| AUC | 0.731 | 0.727 | **-0.004** |
| Share flagged at score >= 70 | 29.6% | 49.3% | +19.7pp |
| Precision of that flag | 76.8% | 70.9% | -5.9pp |
| Recall of that flag | 44.0% | 65.0% | +21.0pp |

The distribution moved substantially and the ability to separate good applications from bad
ones did not improve at all. Population Stability Index across the release is 0.196, inside
the conventional 0.10 to 0.25 "investigate" band. The rule scorer, running on the same
applications over the same period and unchanged, has a PSI of 0.004. That is a clean
control: the applicant pool did not move, the model did.

The calibration curves make the practical consequence concrete. The same score now means
something different:

| LLM score band | Positive rate under v1 | Positive rate under v2 |
|---|---|---|
| 60 to 70 | 56.2% | 43.8% |
| 70 to 80 | 71.1% | 61.9% |
| 80 to 90 | 83.3% | 77.9% |

A v2 score of 70 is worth roughly a v1 score of 60. Nobody moved the threshold, so the
number of applications carrying a "strong candidate" flag jumped by two thirds while the
flag itself became less trustworthy. Whether that trade is good depends on whether
recruiter capacity is the constraint, which is a product decision, but right now it was
made by accident rather than chosen.

**Proposal for the LLM scorer team.** Recalibrate v2 onto the v1 scale before comparing
anything, either by mapping v2 scores to v1 score quantiles or by raising the flag
threshold from 70 to roughly 78, which restores the old flag rate. Then make this
automatic: the `/api/quality-gate` endpoint in this repo runs the same PSI comparison
against the previous version and returns pass, warn or fail. Wire it into the release
pipeline so a distribution shift blocks a rollout instead of being found five months later.
Report AUC and PSI together in every release note, since this release would have looked
like an improvement on either mean score or flag recall alone.

---

## Finding 4: Austrian candidates receive a systematic LLM bonus that outcomes do not justify

**Evidence.** Mean `llm_score` is 69.0 for applications to Austrian jobs and 62.6 for
German ones, a gap of 6.4 points. Positive rates are 53.6% and 51.9%, a difference far too
small to explain it.

The gap is not a confound. It survives inside each model version (v1: AT 65.4, DE 59.0;
v2: AT 73.3, DE 66.7) and inside both profile completeness groups (thin: AT 74.5, DE 73.5;
complete: AT 67.4, DE 60.2). The rule scorer shows no such pattern, scoring AT slightly
*lower* at 0.456 against 0.482. So this is specific to the LLM.

The consequence shows up in ranking quality: the LLM's AUC in Austria is 0.706 against
0.737 in Germany. An inflated, compressed score band discriminates less well within itself.

**Why it matters more than its size suggests.** This is a recruiting platform operating
under EU employment law. A scoring system that gives one nationality a systematic advantage
unrelated to outcomes is a compliance exposure, not just an accuracy problem, and it is the
kind of finding that is far cheaper to fix now than to explain later. The mechanism is
worth investigating directly, since the most likely candidates are country-correlated
signals in the profile text, such as qualification names or employer names, which the model
is treating as quality signals.

**Proposal for the LLM scorer team.** Add country to the standing evaluation set as a
protected dimension and gate releases on the score gap staying inside a defined tolerance
once outcome rates are controlled for. Run an ablation with country identifying details
masked from the prompt to find out how much of the gap is the country signal itself. Until
then, calibrate scores within country rather than globally, which removes the bias from any
cross-country comparison at effectively no cost.

---

## Finding 5: recruiters have quietly disengaged from the AI panel, and the obvious explanation is wrong

**Evidence.** Share of applications where a recruiter opened the AI score, by application
month:

| Period | AI score viewed | Profile opened |
|---|---|---|
| Sep to Dec 2025 | 68.6% to 71.7% | 92.0% to 93.3% |
| Jan to Jul 2026 | 57.5% to 62.6% | 89.7% to 92.1% |

AI panel engagement fell about 10 points and stayed down. Profile opens did not move.
Recruiters are still working the queue at the same rate, they have just stopped consulting
the AI while doing it. Trust in a feature is the leading indicator of whether it survives,
so this is worth escalating regardless of the scorers' accuracy.

**The trap.** Cut the same data by model version and it looks like an open and shut case:
66.4% of v1-era applications had the AI score viewed against 59.5% of v2-era ones. The
natural conclusion is that v2 damaged recruiter trust. The time series rules that out. The
drop happens at the December to January boundary, and v2 did not ship until March. Whatever
caused this preceded the model change by two months, and attributing it to v2 would send the
LLM team to investigate a release that is not responsible.

Two candidate explanations remain and the event data cannot separate them: a UI or workflow
change in early January, or a team or process change at the turn of the year. That question
needs a release log and a conversation with the recruiting team, not more SQL.

**A note on the event data.** `shortlisted` cannot be used as an input to any of this. All
2,467 shortlisted applications end as interviewed or hired, a positive rate of exactly
1.000, against 13.5% for the rest. The event records the decision rather than predicting
it, so treating it as a behavioural signal would leak the outcome into every model built on
it. It is used here only to describe the funnel.

**Proposal for the product team.** Pull the January 2026 release log and interview a
handful of recruiters before building anything. Then instrument the missing half of the
loop: the platform currently records that a score was viewed but not whether the recruiter
agreed with it. A one-click agree or disagree control on the AI panel would produce the
signal every finding above is currently forced to approximate through
`recruiter_decision`, and it would do so without the circularity described in the method
section.

---

## Limitations

- **The label is contaminated.** Recruiters see both scores before deciding, so the scores
  partly cause the outcomes they are graded against. All AUC figures are upper bounds.
  Genuine measurement needs either a holdout where scores are hidden or the explicit
  agree/disagree signal proposed above.
- **`interviewed` is treated as a success.** It is a proxy for the recruiter's judgement,
  not for the candidate performing well in the job. No post-hire outcome exists in this
  data, so nothing here measures whether the platform finds *good* employees, only whether
  it predicts recruiter behaviour.
- **Pending applications are dropped.** All 504 of them. I checked this is defensible: the
  pending rate is between 7.5% and 9.1% across every job family, country, seniority and
  model version, is flat across months, and pending applications have near-identical mean
  scores to decided ones (LLM 64.4 against 64.3). It looks missing-at-random, so
  complete-case analysis is sound. If pending rates ever diverge by segment this assumption
  needs revisiting.
- **The Healthcare rescale factor of 4.04 is descriptive.** It is derived from the observed
  ratio between family means, not from reading the scoring code. It is strong enough to
  locate the bug, not to be applied as a patch.
- **243 duplicate candidate and job pairs** are kept as separate applications, since each
  carries its own scores and decision. If they are genuine resubmissions rather than repeat
  applications, the affected candidates are slightly overweighted.
- **`rule_fit` has an inconsistent tie rule.** Of the 12 applications scoring exactly 0.500,
  ten are bucketed `medium` and two `low`. Cosmetically small, but it means the bucketing
  is not a pure function of the score.
- **Country is the job's country, not the candidate's.** 94.3% of applications are
  same-country so the distinction rarely matters, but the 339 cross-border applications are
  counted in the market they applied into.

---

## What to do first

1. **Fix the Healthcare normalisation in the rule scorer.** Largest effect, a real bug
   rather than a tuning question, and it currently makes the platform draw the wrong
   conclusion about which of its two systems is better.
2. **Recalibrate v2, or raise the flag threshold to about 78.** Small change, immediate
   effect on the precision of what recruiters are shown today.
3. **Ship the release quality gate.** Findings 1 and 3 are both things an automated check
   would have caught at release time instead of months later.
4. **Investigate the January engagement drop before touching the models.** It is the only
   finding that points at the product rather than the scorers, and it is currently being
   misattributed to v2.
5. **Add the agree or disagree control.** It is the only item here that improves the
   measurement itself rather than the thing being measured, so every future analysis
   depends on it.
