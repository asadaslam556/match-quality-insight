import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { get } from "../api";
import Panel from "../components/Panel";
import { num, pct } from "../components/format";
import type { Segment } from "../types";

const RULE = "#1f6feb";
const LLM = "#d97706";

const DIMENSIONS = [
  { value: "job_family", label: "Job family" },
  { value: "profile_band", label: "Profile completeness" },
  { value: "country", label: "Country" },
  { value: "model_version", label: "LLM model version" },
  { value: "seniority", label: "Seniority" },
];

// A job family whose applications are all bucketed low cannot be a real property of the
// candidates in it, so the row is called out in the table.
const ALL_LOW_FIT = 0.999;

export default function Segments() {
  const [dimension, setDimension] = useState("job_family");
  const [segments, setSegments] = useState<Segment[]>();
  const [error, setError] = useState<string>();

  useEffect(() => {
    setSegments(undefined);
    get<{ segments: Segment[] }>("segments", { dimension })
      .then((data) => setSegments(data.segments))
      .catch((cause: Error) => setError(cause.message));
  }, [dimension]);

  if (error) return <div className="state" data-error="true">Could not reach the API: {error}</div>;

  const hasSmallSample = segments?.some((segment) => segment.is_small_sample);

  return (
    <>
      <div className="controls">
        <label htmlFor="dimension">Break down by</label>
        <select id="dimension" value={dimension} onChange={(event) => setDimension(event.target.value)}>
          {DIMENSIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>

      {!segments ? (
        <div className="state">Loading segment...</div>
      ) : (
        <>
          <Panel
            title="Predictive power per segment"
            note="AUC for each scorer inside each segment. A scorer that ranks well everywhere should show a flat profile here; a dip singles out a segment where it fails."
          >
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={segments} margin={{ top: 8, right: 16, bottom: 4, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="segment" />
                <YAxis domain={[0.5, 0.85]} tickFormatter={(value: number) => value.toFixed(2)} />
                <Tooltip formatter={(value) => Number(value).toFixed(4)} />
                <Legend />
                <Bar dataKey="rule_auc" name="Rule scorer AUC" fill={RULE} />
                <Bar dataKey="llm_auc" name="LLM scorer AUC" fill={LLM} />
              </BarChart>
            </ResponsiveContainer>
          </Panel>

          <Panel
            title="Mean score per segment against the outcome it should track"
            note="Mean scores are on their own scales, so compare each series against the positive rate rather than against each other. A segment where the score moves but the outcome does not is a scoring bias, not a real difference in candidate quality."
          >
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={segments} margin={{ top: 8, right: 16, bottom: 4, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="segment" />
                <YAxis yAxisId="left" domain={[0, 100]} />
                <YAxis
                  yAxisId="right"
                  orientation="right"
                  domain={[0, 1]}
                  tickFormatter={(value: number) => `${(value * 100).toFixed(0)}%`}
                />
                <Tooltip />
                <Legend />
                <Bar yAxisId="left" dataKey="mean_llm_score" name="Mean LLM score (0-100)" fill={LLM} />
                <Bar yAxisId="right" dataKey="positive_rate" name="Positive outcome rate" fill="#64748b" />
              </BarChart>
            </ResponsiveContainer>
          </Panel>

          <Panel title="Segment detail">
            <table>
              <thead>
                <tr>
                  <th>Segment</th>
                  <th>Applications</th>
                  <th>Decided</th>
                  <th>Positive rate</th>
                  <th>95% interval</th>
                  <th>Mean rule</th>
                  <th>Mean LLM</th>
                  <th>Bucketed low</th>
                  <th>Rule AUC</th>
                  <th>LLM AUC</th>
                </tr>
              </thead>
              <tbody>
                {segments.map((segment) => (
                  <tr key={segment.segment}>
                    <td className={segment.is_small_sample ? "small-sample" : undefined}>
                      {segment.segment}
                    </td>
                    <td>{segment.applications.toLocaleString()}</td>
                    <td>{segment.decided.toLocaleString()}</td>
                    <td>{pct(segment.positive_rate)}</td>
                    <td>
                      {segment.positive_rate_ci
                        ? `${pct(segment.positive_rate_ci[0])} to ${pct(segment.positive_rate_ci[1])}`
                        : "n/a"}
                    </td>
                    <td>{num(segment.mean_rule_score)}</td>
                    <td>{num(segment.mean_llm_score, 1)}</td>
                    <td className={segment.low_fit_rate >= ALL_LOW_FIT ? "flag" : undefined}>
                      {pct(segment.low_fit_rate)}
                    </td>
                    <td>{num(segment.rule_auc)}</td>
                    <td>{num(segment.llm_auc)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {hasSmallSample && (
              <p className="note" style={{ marginTop: 12, marginBottom: 0 }}>
                * Fewer than 30 decided applications. Read the interval, not the point estimate.
              </p>
            )}
          </Panel>
        </>
      )}
    </>
  );
}
