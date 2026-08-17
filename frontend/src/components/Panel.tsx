import type { ReactNode } from "react";

type Props = { title: string; note?: string; children: ReactNode };

export default function Panel({ title, note, children }: Props) {
  return (
    <section className="panel">
      <h2>{title}</h2>
      {note && <p className="note">{note}</p>}
      {children}
    </section>
  );
}
