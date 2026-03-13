/**
 * TimeRangeSelector - Styled pill button group for time range selection.
 */

import { useState } from "react";

const ranges = ["24h", "7d", "30d", "90d", "Custom"];

export function TimeRangeSelector({ onSelect = () => {} }) {
  const [selected, setSelected] = useState("30d");

  const handleSelect = (range) => {
    setSelected(range);
    onSelect(range);
  };

  return (
    <div className="flex gap-2 flex-wrap">
      {ranges.map((range) => (
        <button
          key={range}
          onClick={() => handleSelect(range)}
          className={`
            px-4 py-2 rounded-full text-sm font-medium transition-all duration-200
            ${
              selected === range
                ? "bg-sky-500/20 text-sky-400 border border-sky-500/50"
                : "bg-white/5 text-gray-400 border border-white/10 hover:bg-white/10 hover:text-gray-300"
            }
          `}
        >
          {range}
        </button>
      ))}
    </div>
  );
}
