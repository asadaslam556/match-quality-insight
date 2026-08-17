type Props = { label: string; value: string; sub?: string };

export default function KpiCard({ label, value, sub }: Props) {
  return (
    <div className="kpi">
      <div className="label">{label}</div>
      <div className="value">{value}</div>
      {sub && <div className="sub">{sub}</div>}
    </div>
  );
}
