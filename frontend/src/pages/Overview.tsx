import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { get } from "../api";
import KpiCard from "../components/KpiCard";
import Panel from "../components/Panel";
import { num, pct } from "../components/format";
import type { Agreement, CalibrationBand, MonthlyEngagement, Funnel, Overview as OverviewData } from "../types";

const RULE = "#1f6feb";
const LLM = "#d97706";

const GATE_COPY: Record<string, string> = {
  pass: "Score distribution is stable across the model change.",
  warn: "Score distribution shifted enough to need a threshold review.",
  fail: "Score distribution shifted materially. Thresholds are no longer valid.",
  skipped: "Only one model version present, nothing to compare.",
};

export default function Overview() {
  const [overview, setOverview] = useState<OverviewData>();
  const [agreement, setAgreement] = useState<Agreement>();
  const [calibration, setCalibration] = useState<CalibrationBand[]>();
  const [monthly, setMonthly] = useState<MonthlyEngagement[]>();
  const [funnel, setFunnel] = useState<Funnel>();
  const [error, setError] = useState<string>();

  useEffect(() => {
    Promise.all([
      get<OverviewData>("overview"),
      get<Agreement>("agreement", { exclude_family: "Healthcare" }),
      get<{ bands: CalibrationBand[] }>("calibration", { scorer: "llm" }),
      get<{ monthly: MonthlyEngagement[]; funnel: Funnel }>("recruiter-behaviour"),
    ])
      .then(([overviewData, agreementData, calibrationData, behaviour]) => {
        setOverview(overviewData);
        setAgreement(agreementData);
        setCalibration(calibrationData.bands);
        setMonthly(behaviour.monthly);
        setFunnel(behaviour.funnel);
      })
      .catch((cause: Error) => setError(cause.message));
  }, []);

  if (error) return <div className="state" data-error="true">Could not reach the API: {error}</div>;
  if (!overview || !agreement || !calibration || !monthly || !funnel) {
    return <div className="state">Loading metrics...</div>;
  }

  const { counts, pooled, excluding_healthcare: withoutHealthcare, quality_gate: gate } = overview;

  const aucComparison = [
    { view: "All job families", rule: pooled.rule, llm: pooled.llm },
    { view: "Excluding Healthcare", rule: withoutHealthcare.rule, llm: withoutHealthcare.llm },
  ];

  // One series per model version, joined on the shared score band.
  const versions = [...new Set(calibration.map((band) => band.llm_model_version))].sort();
  const calibrationByBand = [...new Set(calibration.map((band) => band.band))]
    .sort((a, b) => a - b)
    .map((band) => {
      const row: Record<string, string | number | null> = {
        band: calibration.find((entry) => entry.band === band)!.band_label,
      };
      versions.forEach((version) => {
        const match = calibration.find(
          (entry) => entry.band === band && entry.llm_model_version === version,
        );
        // Bands under 30 decided applications are dropped rather than drawn as noise.
        row[version] = match && !match.is_small_sample ? match.positive_rate : null;
      });
      return row;
    });

  return (
    <>
      <div className="kpis">
        <KpiCard
          label="Applications"
          value={counts.total_applications.toLocaleString()}
          sub={`${counts.jobs} jobs, ${counts.candidates.toLocaleString()} candidates`}
        />
        <KpiCard
          label="Decided"
          value={counts.decided.toLocaleString()}
          sub={`${counts.pending} still pending (${pct(counts.pending_rate)})`}
        />
        <KpiCard
          label="Positive outcome rate"
          value={pct(counts.positive_rate)}
          sub={`${pct(counts.hire_rate)} hired`}
        />
        <KpiCard
          label="Rule scorer AUC"
          value={num(withoutHealthcare.rule)}
          sub={`${num(pooled.rule)} including Healthcare`}
        />
        <KpiCard
          label="LLM scorer AUC"
          value={num(withoutHealthcare.llm)}
          sub={`${num(pooled.llm)} including Healthcare`}
        />
      </div>

      <div className="banner" data-status={gate.status}>
        <h3>
          Release quality gate: {gate.status.toUpperCase()}
          {gate.baseline_version && ` (${gate.baseline_version} to ${gate.current_version})`}
        </h3>
        <p>
          {GATE_COPY[gate.status]}
          {gate.llm_psi != null && (
            <>
              {" "}
              LLM score PSI {num(gate.llm_psi)} against a {num(gate.warn_at, 2)} warning line. The
              unchanged rule scorer moved only {num(gate.rule_psi_control)} over the same
              applications, so the shift came from the model rather than the applicant pool.
            </>
          )}
          {gate.flag_rate_at_threshold && (
            <>
              {" "}
              Share of applications flagged at score {gate.flag_rate_at_threshold.threshold} went from{" "}
              {pct(gate.flag_rate_at_threshold.baseline)} to {pct(gate.flag_rate_at_threshold.current)}.
            </>
          )}
        </p>
      </div>

      <Panel
        title="Which scorer actually predicts recruiter decisions?"
        note="AUC is the chance a random positive outcome is ranked above a random negative one. Read the two views together: pooling every job family reverses the ranking of the two scorers, because one broken segment drags the rule scorer's pooled figure down."
      >
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={aucComparison} margin={{ top: 8, right: 16, bottom: 4, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="view" />
            <YAxis domain={[0.5, 0.85]} tickFormatter={(value: number) => value.toFixed(2)} />
            <Tooltip formatter={(value) => Number(value).toFixed(4)} />
            <Legend />
            <Bar dataKey="rule" name="Rule scorer" fill={RULE} />
            <Bar dataKey="llm" name="LLM scorer" fill={LLM} />
          </BarChart>
        </ResponsiveContainer>
      </Panel>

      <Panel
        title="Is a score of 80 really better than a score of 60?"
        note="Observed positive rate for each LLM score band, one line per model version. Two separated lines mean the same number carries a different meaning depending on which model produced it. Bands with fewer than 30 decided applications are omitted."
      >
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={calibrationByBand} margin={{ top: 8, right: 16, bottom: 4, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="band" />
            <YAxis domain={[0, 1]} tickFormatter={(value: number) => `${(value * 100).toFixed(0)}%`} />
            <Tooltip formatter={(value) => pct(Number(value))} />
            <Legend />
            {versions.map((version, index) => (
              <Line
                key={version}
                type="monotone"
                dataKey={version}
                stroke={index === 0 ? RULE : LLM}
                strokeWidth={2}
                connectNulls
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </Panel>

      <Panel
        title="Are recruiters still looking at the AI output?"
        note="Share of applications reaching each interaction stage, by application month. Profile opens hold steady while AI score views fall away, so this is disengagement from the AI panel specifically rather than from the queue."
      >
        <ResponsiveContainer width="100%" height={260}>
          <LineChart data={monthly} margin={{ top: 8, right: 16, bottom: 4, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="month" />
            <YAxis domain={[0, 1]} tickFormatter={(value: number) => `${(value * 100).toFixed(0)}%`} />
            <Tooltip formatter={(value) => pct(Number(value))} />
            <Legend />
            <Line type="monotone" dataKey="profile_opened_rate" name="Profile opened" stroke={RULE} strokeWidth={2} />
            <Line type="monotone" dataKey="ai_score_viewed_rate" name="AI score viewed" stroke={LLM} strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </Panel>

      <Panel
        title="Where the two scorers disagree, excluding Healthcare"
        note="Each scorer is split at its own median. The two disagreement rows are the ones that matter: they show which scorer to believe when only one of them likes an application."
      >
        <table>
          <thead>
            <tr>
              <th>Quadrant</th>
              <th>Applications</th>
              <th>Positive rate</th>
            </tr>
          </thead>
          <tbody>
            {agreement.quadrants.map((quadrant) => (
              <tr key={quadrant.quadrant}>
                <td>{quadrant.quadrant.replace(/_/g, " ")}</td>
                <td>{quadrant.decided.toLocaleString()}</td>
                <td>{pct(quadrant.positive_rate)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="note" style={{ marginTop: 12, marginBottom: 0 }}>
          The two scorers agree on {pct(agreement.agreement_rate)} of applications. On the rest the{" "}
          <strong>{agreement.winner_on_disagreement}</strong> scorer is the one to follow. Note that{" "}
          {funnel.shortlisted.toLocaleString()} shortlisted applications convert at{" "}
          {pct(funnel.positive_rate_when_shortlisted)}, which confirms shortlisting records the decision
          rather than predicting it, so it is never used as an input above.
        </p>
      </Panel>
    </>
  );
}
