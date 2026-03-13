/**
 * Step 2: Choose Integration Method - Select proxy, SDK, or log connector.
 */

import { useState } from "react";
import { motion } from "framer-motion";
import { integrationMethods } from "../mockData";
import { GlassPanel } from "../../../components/GlassPanel";

export function ChooseIntegration({ onNext }) {
  const [selected, setSelected] = useState(null);

  const handleContinue = () => {
    if (selected) {
      const method = integrationMethods.find((m) => m.id === selected);
      onNext({ integrationMethod: method.id });
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, x: 40 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -40 }}
      transition={{ duration: 0.3 }}
      className="w-full max-w-2xl"
    >
      <div className="space-y-6">
        {/* Header */}
        <div className="text-center">
          <h2 className="text-2xl font-bold text-white mb-2">
            Choose Your Integration Method
          </h2>
          <p className="text-sm text-zinc-400">
            Pick the easiest way to connect your LLM infrastructure to Staxx
          </p>
        </div>

        {/* Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {integrationMethods.map((method) => {
            const Icon = method.icon;
            const isSelected = selected === method.id;
            const isRecommended = method.badge === "Recommended";

            return (
              <motion.button
                key={method.id}
                onClick={() => setSelected(method.id)}
                whileHover={{ scale: 1.02, y: -4 }}
                whileTap={{ scale: 0.98 }}
                className={`
                  relative p-6 rounded-lg border-2 transition-all duration-200
                  ${
                    isSelected
                      ? "bg-green-500/10 border-green-500 shadow-lg shadow-green-500/20"
                      : "bg-white/3 border-white/10 hover:border-white/20"
                  }
                `}
              >
                {/* Recommended Badge */}
                {isRecommended && (
                  <div className="absolute -top-2 -right-2">
                    <span className="px-3 py-1 rounded-full text-xs font-bold
                      bg-green-500 text-white shadow-lg">
                      Recommended
                    </span>
                  </div>
                )}

                {/* Icon */}
                <div className={`
                  w-12 h-12 rounded-lg flex items-center justify-center mb-4
                  ${
                    isSelected
                      ? "bg-green-500/30 border border-green-500/50"
                      : "bg-white/5 border border-white/10"
                  }
                `}>
                  <Icon
                    size={24}
                    className={isSelected ? "text-green-400" : "text-zinc-300"}
                  />
                </div>

                {/* Content */}
                <h3 className="text-lg font-bold text-white text-left mb-1">
                  {method.name}
                </h3>
                <p className="text-xs text-zinc-400 text-left mb-4">
                  {method.description}
                </p>

                {/* Metadata */}
                <div className="flex items-center justify-between text-xs">
                  <span className="text-zinc-500">{method.setupTime}</span>
                  <span className={`
                    px-2 py-1 rounded-md font-medium
                    ${
                      method.complexity === "Easy"
                        ? "bg-green-500/20 text-green-400"
                        : method.complexity === "Medium"
                        ? "bg-amber-500/20 text-amber-400"
                        : "bg-purple-500/20 text-purple-400"
                    }
                  `}>
                    {method.complexity}
                  </span>
                </div>

                {/* Selection Indicator */}
                {isSelected && (
                  <motion.div
                    layoutId="selectIndicator"
                    className="absolute inset-0 rounded-lg border-2 border-green-500 pointer-events-none"
                    transition={{ duration: 0.2 }}
                  />
                )}
              </motion.button>
            );
          })}
        </div>

        {/* Continue Button */}
        <div className="flex gap-4 pt-4">
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            disabled={!selected}
            onClick={handleContinue}
            className="flex-1 py-3 rounded-lg bg-green-500 hover:bg-green-600 disabled:bg-zinc-700
              text-white font-semibold transition-all disabled:cursor-not-allowed"
          >
            Continue →
          </motion.button>
        </div>
      </div>
    </motion.div>
  );
}
