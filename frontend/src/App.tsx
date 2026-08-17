import { useState } from "react";

import Overview from "./pages/Overview";
import Segments from "./pages/Segments";

const TABS = [
  { id: "overview", label: "Overview", render: () => <Overview /> },
  { id: "segments", label: "Segments", render: () => <Segments /> },
];

export default function App() {
  const [active, setActive] = useState("overview");

  return (
    <div className="shell">
      <header>
        <h1>Match Quality Insight</h1>
        <p>How well the rule-based and LLM scorers predict what recruiters actually do.</p>
      </header>

      <nav>
        {TABS.map((tab) => (
          <button key={tab.id} data-active={tab.id === active} onClick={() => setActive(tab.id)}>
            {tab.label}
          </button>
        ))}
      </nav>

      {TABS.find((tab) => tab.id === active)!.render()}
    </div>
  );
}
