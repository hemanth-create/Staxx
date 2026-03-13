/**
 * Sidebar - Left navigation with glassmorphic styling.
 */

import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { motion } from "framer-motion";
import {
  LayoutDashboard,
  Network,
  Zap,
  TrendingUp,
  BarChart3,
  AlertCircle,
  Settings,
  ChevronDown,
  Menu,
  X,
} from "lucide-react";

const navItems = [
  { label: "Dashboard", icon: LayoutDashboard, href: "/" },
  { label: "Cost Topology", icon: Network, href: "/cost-topology" },
  { label: "Shadow Evals", icon: Zap, href: "/shadow-evals" },
  {
    label: "Swap Recommendations",
    icon: TrendingUp,
    href: "/recommendations",
  },
  { label: "ROI Projections", icon: BarChart3, href: "/roi" },
  { label: "Alerts", icon: AlertCircle, href: "/alerts" },
  { label: "Settings", icon: Settings, href: "/settings" },
];

export function Sidebar() {
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);

  const isActive = (href) => location.pathname === href;

  const sidebarVariants = {
    open: { x: 0 },
    closed: { x: "-100%" },
  };

  return (
    <>
      {/* Mobile Menu Button */}
      <button
        onClick={() => setMobileOpen(!mobileOpen)}
        className="fixed top-4 left-4 z-50 md:hidden p-2 rounded-lg bg-white/5 border border-white/10 text-gray-400 hover:text-white"
      >
        {mobileOpen ? <X size={20} /> : <Menu size={20} />}
      </button>

      {/* Sidebar */}
      <aside
        className={`fixed left-0 top-0 z-40 h-screen w-60 md:z-0 md:relative
          bg-zinc-950 border-r border-white/10 backdrop-blur-xl
          flex flex-col p-6 gap-8 transition-transform duration-300 md:translate-x-0
          ${mobileOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"}`}
      >
        {/* Logo */}
        <div className="flex items-center gap-3 pt-4">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-sky-500 to-blue-600 flex items-center justify-center">
            <span className="text-white font-bold text-lg">S</span>
          </div>
          <h1 className="text-lg font-bold text-white">Staxx</h1>
        </div>

        {/* Navigation */}
        <nav className="flex-1 space-y-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = isActive(item.href);

            return (
              <Link
                key={item.href}
                to={item.href}
                onClick={() => setMobileOpen(false)}
              >
                <motion.button
                  whileHover={{ x: 4 }}
                  className={`
                    w-full flex items-center gap-3 px-4 py-3 rounded-lg
                    transition-all duration-200 text-sm font-medium
                    ${
                      active
                        ? "bg-white/8 text-sky-400 border-l-2 border-sky-500"
                        : "text-gray-400 hover:text-gray-300 hover:bg-white/5"
                    }
                  `}
                >
                  <Icon size={18} />
                  <span>{item.label}</span>
                </motion.button>
              </Link>
            );
          })}
        </nav>

        {/* Organization Switcher */}
        <div className="border-t border-white/10 pt-6">
          <button
            className="w-full flex items-center justify-between
            px-4 py-3 rounded-lg bg-white/5 border border-white/10
            text-gray-400 hover:text-gray-300 hover:bg-white/8
            transition-all duration-200"
          >
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-sky-500/20 flex items-center justify-center text-xs font-bold text-sky-400">
                AC
              </div>
              <div className="text-left">
                <p className="text-xs font-semibold text-gray-300">
                  Acme Corp
                </p>
                <p className="text-xs text-gray-500">Owner</p>
              </div>
            </div>
            <ChevronDown size={16} />
          </button>
        </div>
      </aside>

      {/* Mobile Overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/50 md:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}
    </>
  );
}
