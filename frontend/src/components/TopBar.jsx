/**
 * TopBar - Sticky header with breadcrumb, search, time range, notifications, and user menu.
 */

import { useState } from "react";
import { useLocation } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  Search,
  Bell,
  ChevronDown,
  LogOut,
  User,
  CreditCard,
} from "lucide-react";
import { TimeRangeSelector } from "./TimeRangeSelector";
import { GlassPanel } from "./GlassPanel";

// Breadcrumb mapping
const breadcrumbMap = {
  "/": "Dashboard",
  "/cost-topology": "Cost Topology",
  "/shadow-evals": "Shadow Evaluations",
  "/recommendations": "Swap Recommendations",
  "/roi": "ROI Projections",
  "/alerts": "Alerts",
  "/settings": "Settings",
};

export function TopBar() {
  const location = useLocation();
  const [userMenuOpen, setUserMenuOpen] = useState(false);

  const breadcrumb = breadcrumbMap[location.pathname] || "Dashboard";

  return (
    <motion.header
      initial={{ y: -10, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.4 }}
      className="sticky top-0 z-30 border-b border-white/10 backdrop-blur-xl bg-zinc-950/50"
    >
      <div className="px-6 py-4 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        {/* Left: Breadcrumb and Title */}
        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-500">Staxx</span>
          <span className="text-gray-400">/</span>
          <span className="text-sm font-medium text-white">{breadcrumb}</span>
        </div>

        {/* Center: Time Range Selector */}
        <div className="hidden lg:flex">
          <TimeRangeSelector />
        </div>

        {/* Right: Search, Notifications, User Menu */}
        <div className="flex items-center gap-3 ml-auto">
          {/* Search Bar */}
          <GlassPanel
            className="hidden md:flex w-64 lg:w-80"
            innerClassName="flex items-center gap-2"
            noPadding={true}
          >
            <div className="px-3 py-2 flex items-center gap-2 w-full">
              <Search size={16} className="text-gray-500" />
              <input
                type="text"
                placeholder="Search metrics..."
                className="bg-transparent outline-none text-sm text-gray-300 placeholder-gray-600 w-full"
              />
            </div>
          </GlassPanel>

          {/* Notification Bell */}
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            className="relative p-2 rounded-lg bg-white/5 border border-white/10 text-gray-400
            hover:text-white hover:bg-white/8 transition-all"
          >
            <Bell size={18} />
            <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full" />
          </motion.button>

          {/* User Menu */}
          <div className="relative">
            <motion.button
              whileHover={{ scale: 1.05 }}
              onClick={() => setUserMenuOpen(!userMenuOpen)}
              className="p-2 rounded-lg bg-white/5 border border-white/10 text-gray-400
              hover:text-white hover:bg-white/8 transition-all flex items-center gap-2"
            >
              <div className="w-6 h-6 rounded-full bg-sky-500 flex items-center justify-center text-xs font-bold text-white">
                A
              </div>
              <ChevronDown
                size={16}
                className={`transition-transform ${
                  userMenuOpen ? "rotate-180" : ""
                }`}
              />
            </motion.button>

            {/* User Menu Dropdown */}
            <AnimatePresence>
              {userMenuOpen && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className="absolute right-0 mt-2 w-48 rounded-lg backdrop-blur-xl bg-zinc-900/95
                  border border-white/10 shadow-2xl overflow-hidden"
                >
                <div className="p-3 border-b border-white/10">
                  <p className="text-sm font-medium text-white">
                    acme@company.com
                  </p>
                  <p className="text-xs text-gray-500">Acme Corp</p>
                </div>
                <nav className="space-y-1 p-2">
                  <button className="w-full flex items-center gap-2 px-3 py-2 rounded-lg
                  text-gray-400 hover:text-white hover:bg-white/5 text-sm transition-all">
                    <User size={16} />
                    Profile
                  </button>
                  <button className="w-full flex items-center gap-2 px-3 py-2 rounded-lg
                  text-gray-400 hover:text-white hover:bg-white/5 text-sm transition-all">
                    <CreditCard size={16} />
                    Billing
                  </button>
                </nav>
                <button className="w-full flex items-center gap-2 px-3 py-2 text-gray-400 hover:text-red-400
                hover:bg-red-500/10 text-sm transition-all border-t border-white/10">
                  <LogOut size={16} />
                  Sign Out
                </button>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>

      {/* Mobile Time Range Selector */}
      <div className="lg:hidden px-6 pb-4">
        <TimeRangeSelector />
      </div>
    </motion.header>
  );
}
