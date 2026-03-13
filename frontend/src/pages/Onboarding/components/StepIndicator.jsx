/**
 * StepIndicator - Progress indicator for onboarding wizard.
 * Shows numbered steps with completion status.
 */

import { motion } from "framer-motion";
import { CheckCircle2 } from "lucide-react";

export function StepIndicator({ currentStep, steps }) {
  return (
    <div className="flex items-center justify-center gap-8 mb-12">
      {steps.map((label, idx) => {
        const stepNumber = idx + 1;
        const isActive = stepNumber === currentStep;
        const isCompleted = stepNumber < currentStep;

        return (
          <motion.div
            key={stepNumber}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: idx * 0.05 }}
            className="flex flex-col items-center"
          >
            {/* Step Circle */}
            <motion.div
              className={`
                w-12 h-12 rounded-full flex items-center justify-center
                font-bold text-sm transition-all duration-300
                ${
                  isActive
                    ? "bg-green-500 border-2 border-green-400 text-white shadow-lg shadow-green-500/50"
                    : isCompleted
                    ? "bg-green-500/20 border-2 border-green-500/50 text-green-400"
                    : "bg-zinc-800/50 border-2 border-zinc-700 text-zinc-400"
                }
              `}
              whileHover={!isActive ? { scale: 1.05 } : {}}
            >
              {isCompleted ? (
                <CheckCircle2 size={20} />
              ) : (
                <span>{stepNumber}</span>
              )}
            </motion.div>

            {/* Label */}
            <p
              className={`
                mt-3 text-xs font-medium text-center w-20
                ${isActive ? "text-white" : "text-zinc-400"}
              `}
            >
              {label}
            </p>

            {/* Connector Line */}
            {stepNumber < steps.length && (
              <motion.div
                className={`
                  h-1 w-8 absolute left-[calc(50%+24px)] top-6
                  ${
                    isCompleted || isActive
                      ? "bg-green-500"
                      : "bg-zinc-700"
                  }
                `}
                initial={{ scaleX: 0 }}
                animate={{ scaleX: 1 }}
                transition={{ delay: idx * 0.1 + 0.2 }}
              />
            )}
          </motion.div>
        );
      })}
    </div>
  );
}
