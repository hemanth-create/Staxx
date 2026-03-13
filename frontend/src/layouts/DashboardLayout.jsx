/**
 * DashboardLayout - Main application layout wrapper with sidebar and top bar.
 */

import { Sidebar } from "../components/Sidebar";
import { TopBar } from "../components/TopBar";
import { motion } from "framer-motion";

export function DashboardLayout({ children }) {
  return (
    <div className="flex h-screen bg-zinc-950 text-white overflow-hidden">
      {/* Sidebar */}
      <Sidebar />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top Bar */}
        <TopBar />

        {/* Page Content */}
        <motion.main
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          transition={{ duration: 0.3 }}
          className="flex-1 overflow-auto"
        >
          <div className="p-6 md:p-8 w-full">
            {children}
          </div>
        </motion.main>
      </div>
    </div>
  );
}
