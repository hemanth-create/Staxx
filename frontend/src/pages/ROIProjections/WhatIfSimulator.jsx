/**
 * WhatIfSimulator - Interactive panel to adjust implementation rate.
 * Shows Conservative, Expected, and Optimistic scenarios based on CI bounds.
 */

import { useState, useMemo } from "react";
import { motion } from "framer-motion";
import { GlassPanel } from "../../components/GlassPanel";
import { roiSummary, buildProjectionData } from "./mockData";

function WhatIfSimulator({ onRateChange = () => {} }) {
  const [implementationRate, setImplementationRate] = useState(75);

  // Build projection at this rate and extract month 12 values for scenarios
  const projectionData = useMemo(
    () => buildProjectionData(implementationRate / 100),
    [implementationRate]
  );

  const month12 = projectionData[11];

  // Scenarios based on CI bounds
  const scenarios = [
    {
      name: "Conservative",
      monthlyAmount: Math.round(month12.ciLower / 12),
      annualAmount: Math.round(month12.ciLower),
      color: "text-sky-400",
      bgColor: "bg-sky-500/10",
      borderColor: "border-sky-500/30",
      description: "Lower bound (-8%)",
    },
    {
      name: "Expected",
      monthlyAmount: Math.round(month12.cumulativeSavings / 12),
      annualAmount: month12.cumulativeSavings,
      color: "text-green-400",
      bgColor: "bg-green-500/10",
      borderColor: "border-green-500/30",
      description: "Most likely",
    },
    {
      name: "Optimistic",
      monthlyAmount: Math.round(month12.ciUpper / 12),
      annualAmount: Math.round(month12.ciUpper),
      color: "text-purple-400",
      bgColor: "bg-purple-500/10",
      borderColor: "border-purple-500/30",
      description: "Upper bound (+8%)",
    },
  ];

  const handleRateChange = (e) => {
    const newRate = parseInt(e.target.value, 10);
    setImplementationRate(newRate);
    onRateChange(newRate);
  };

  return (
    <GlassPanel>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h3 className="text-lg font-semibold text-white">
            What if you approved all recommendations?
          </h3>
          <p className="text-sm text-zinc-400 mt-1">
            Adjust the implementation rate to see how projected savings change
          </p>
        </div>

        {/* Slider */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium text-zinc-300">Implementation Rate</label>
            <motion.span
              key={implementationRate}
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              className="text-lg font-bold text-green-400"
            >
              {implementationRate}%
            </motion.span>
          </div>

          <div className="relative pt-2 pb-4">
            <input
              type="range"
              min="0"
              max="100"
              value={implementationRate}
              onChange={handleRateChange}
              className="w-full h-2 bg-zinc-700/50 rounded-lg appearance-none cursor-pointer slider"
              style={{
                background: `linear-gradient(to right, rgba(34,197,94,0.3) 0%, rgba(34,197,94,0.3) ${implementationRate}%, rgba(255,255,255,0.1) ${implementationRate}%, rgba(255,255,255,0.1) 100%)`,
              }}
            />

            {/* Slider labels */}
            <div className="flex justify-between mt-2 text-xs text-zinc-500">
              <span>0%</span>
              <span>50%</span>
              <span>100%</span>
            </div>
          </div>

          {/* Inline styles for range slider */}
          <style>{`
            .slider::-webkit-slider-thumb {
              appearance: none;
              width: 18px;
              height: 18px;
              border-radius: 50%;
              background: linear-gradient(135deg, #22c55e, #16a34a);
              cursor: pointer;
              border: 2px solid rgba(255,255,255,0.2);
              box-shadow: 0 0 8px rgba(34,197,94,0.5);
            }
            .slider::-moz-range-thumb {
              width: 18px;
              height: 18px;
              border-radius: 50%;
              background: linear-gradient(135deg, #22c55e, #16a34a);
              cursor: pointer;
              border: 2px solid rgba(255,255,255,0.2);
              box-shadow: 0 0 8px rgba(34,197,94,0.5);
            }
          `}</style>
        </div>

        {/* Scenario Cards */}
        <motion.div
          layout
          className="grid grid-cols-3 gap-4"
        >
          {scenarios.map((scenario, idx) => (
            <motion.div
              key={scenario.name}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.05 }}
              className={`p-4 rounded-lg border ${scenario.bgColor} ${scenario.borderColor} transition-all duration-300`}
            >
              <p className="text-xs font-medium text-zinc-400 mb-1">{scenario.description}</p>
              <p className={`text-sm font-semibold ${scenario.color} mb-2`}>{scenario.name}</p>
              <div className="space-y-1">
                <motion.p
                  key={scenario.monthlyAmount}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="text-xl font-bold text-white"
                >
                  ${(scenario.monthlyAmount / 1000).toFixed(1)}k
                </motion.p>
                <p className="text-xs text-zinc-400">/month</p>
                <p className="text-xs text-zinc-500 mt-2">
                  Annual: ${(scenario.annualAmount / 1000).toFixed(0)}k
                </p>
              </div>
            </motion.div>
          ))}
        </motion.div>

        {/* Info Text */}
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-3 text-xs text-zinc-400">
          <p>
            At <span className="font-semibold text-green-400">{implementationRate}% implementation</span>,
            you can expect monthly savings of <span className="font-semibold text-green-400">
              ${Math.round(scenarios[1].monthlyAmount).toLocaleString()}
            </span>, with a conservative floor of <span className="font-semibold text-sky-400">
              ${Math.round(scenarios[0].monthlyAmount).toLocaleString()}
            </span> and optimistic ceiling of <span className="font-semibold text-purple-400">
              ${Math.round(scenarios[2].monthlyAmount).toLocaleString()}
            </span>.
          </p>
        </div>
      </div>
    </GlassPanel>
  );
}

export default WhatIfSimulator;
