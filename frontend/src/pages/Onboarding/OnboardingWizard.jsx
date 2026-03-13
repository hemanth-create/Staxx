/**
 * OnboardingWizard - Main wizard component orchestrating all steps.
 */

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { StepIndicator } from "./components/StepIndicator";
import { CreateAccount } from "./steps/CreateAccount";
import { ChooseIntegration } from "./steps/ChooseIntegration";
import { IntegrationSetup } from "./steps/IntegrationSetup";
import { FirstData } from "./steps/FirstData";
import { stepLabels } from "./mockData";

function OnboardingWizard() {
  const [step, setStep] = useState(1);
  const [wizardData, setWizardData] = useState({
    email: null,
    token: null,
    apiKey: null,
    orgId: null,
    proxyUrl: null,
    integrationMethod: null,
    connectionTested: false,
  });

  const handleNext = (newData) => {
    setWizardData((prev) => ({ ...prev, ...newData }));
    setStep((prev) => prev + 1);
  };

  const handleBack = () => {
    setStep((prev) => Math.max(prev - 1, 1));
  };

  const renderStep = () => {
    switch (step) {
      case 1:
        return <CreateAccount onNext={handleNext} />;
      case 2:
        return <ChooseIntegration onNext={handleNext} />;
      case 3:
        return (
          <IntegrationSetup
            integrationMethod={wizardData.integrationMethod}
            apiKey={wizardData.apiKey}
            proxyUrl={wizardData.proxyUrl}
            onNext={handleNext}
          />
        );
      case 4:
        return (
          <FirstData
            apiKey={wizardData.apiKey}
            onNext={handleNext}
          />
        );
      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-zinc-950 flex flex-col items-center justify-center p-6 relative">
      {/* Background Gradients */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-green-500/10 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-sky-500/10 rounded-full blur-3xl" />
      </div>

      {/* Centered Content */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-3xl relative z-10"
      >
        {/* Logo & Branding */}
        <div className="flex items-center justify-center mb-12 gap-3">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-green-500 to-sky-500 flex items-center justify-center">
            <span className="text-white font-bold text-lg">S</span>
          </div>
          <h1 className="text-2xl font-bold text-white">Staxx Intelligence</h1>
        </div>

        {/* Step Indicator */}
        <StepIndicator currentStep={step} steps={stepLabels} />

        {/* Step Content */}
        <div className="flex justify-center">
          <AnimatePresence mode="wait">
            <motion.div
              key={step}
              initial={{ opacity: 0, x: 40 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -40 }}
              transition={{ duration: 0.3 }}
            >
              {renderStep()}
            </motion.div>
          </AnimatePresence>
        </div>

        {/* Back Button (except on step 1) */}
        {step > 1 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-8 flex justify-center"
          >
            <button
              onClick={handleBack}
              className="px-6 py-2 text-sm font-medium text-zinc-400 hover:text-white
                border border-zinc-700 hover:border-zinc-600 rounded-lg transition-all"
            >
              ← Back
            </button>
          </motion.div>
        )}
      </motion.div>

      {/* Footer */}
      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.5 }}
        className="absolute bottom-6 text-xs text-zinc-600 text-center"
      >
        Secure • No data stored until you approve • GDPR compliant
      </motion.p>
    </div>
  );
}

export default OnboardingWizard;
