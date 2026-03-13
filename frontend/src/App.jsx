/**
 * App.jsx - Main application entry point with React Router setup.
 */

import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import DashboardHome from "./pages/DashboardHome";
import CostTopologyPage from "./pages/CostTopology/CostTopologyPage";
import ShadowEvalsPage from "./pages/ShadowEvals/ShadowEvalsPage";
import SwapRecommendationsPage from "./pages/SwapRecommendations/SwapRecommendationsPage";
import ROIProjectionsPage from "./pages/ROIProjections/ROIProjectionsPage";
import AlertsPage from "./pages/Alerts/AlertsPage";
import OnboardingWizard from "./pages/Onboarding/OnboardingWizard";

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<DashboardHome />} />
        <Route path="/onboarding" element={<OnboardingWizard />} />
        <Route path="/cost-topology" element={<CostTopologyPage />} />
        <Route path="/shadow-evals" element={<ShadowEvalsPage />} />
        <Route path="/recommendations" element={<SwapRecommendationsPage />} />
        <Route path="/roi" element={<ROIProjectionsPage />} />
        <Route path="/alerts" element={<AlertsPage />} />
        {/* Future routes */}
        {/* <Route path="/settings" element={<Settings />} /> */}
      </Routes>
    </Router>
  );
}

export default App;
