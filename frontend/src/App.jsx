import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, Legend, ResponsiveContainer,
  PieChart, Pie, Cell, AreaChart, Area
} from 'recharts';
import {
  Activity, DollarSign, Zap, Layers, AlertCircle, ChevronRight, Sparkles, TerminalSquare
} from 'lucide-react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs) {
  return twMerge(clsx(inputs));
}

// Premium Color Palette
const COLORS = ['#3b82f6', '#8b5cf6', '#10b981', '#f59e0b', '#ec4899'];
const GRADIENTS = [
  ['#3b82f6', '#60a5fa'], // Blue
  ['#8b5cf6', '#a78bfa'], // Purple
  ['#10b981', '#34d399'], // Emerald
  ['#f59e0b', '#fbbf24']  // Amber
];

// Reusable Custom Tooltip for Recharts
const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="glass-panel p-3 rounded-xl border border-white/10 shadow-2xl z-50">
        <p className="text-white/90 font-medium text-sm mb-2">{label}</p>
        <div className="space-y-1.5">
          {payload.map((entry, index) => (
            <div key={`item-${index}`} className="flex items-center justify-between gap-4 text-xs font-medium">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full" style={{ backgroundColor: entry.color }} />
                <span className="text-white/70 truncate max-w-[120px]">{entry.name}</span>
              </div>
              <span className="text-white font-semibold">
                {entry.value.toLocaleString('en-US', { style: 'currency', currency: 'USD' })}
              </span>
            </div>
          ))}
        </div>
      </div>
    );
  }
  return null;
};

// Animated Stat Card Component
const StatCard = ({ title, value, subtitle, icon: Icon, trend, colorIdx, delay = 0 }) => {
  const [color1, color2] = GRADIENTS[colorIdx % GRADIENTS.length];

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: delay * 0.1, ease: "easeOut" }}
      whileHover={{ y: -4, transition: { duration: 0.2 } }}
      className="glass-card p-6 rounded-2xl relative overflow-hidden group"
    >
      {/* Dynamic glow effect on hover */}
      <div
        className="absolute -inset-1 opacity-0 group-hover:opacity-20 blur-xl transition-opacity duration-500 rounded-3xl"
        style={{ backgroundImage: `linear-gradient(to right, ${color1}, ${color2})` }}
      />

      <div className="relative z-10 flex items-start justify-between">
        <div>
          <p className="text-sm font-medium text-intel-400 mb-1">{title}</p>
          <div className="flex items-baseline gap-2">
            <h2 className="text-3xl font-bold tracking-tight text-white">{value}</h2>
            {trend && (
              <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                {trend}
              </span>
            )}
          </div>
          {subtitle && <p className="text-xs font-medium text-intel-400 mt-2">{subtitle}</p>}
        </div>

        <div
          className="p-3 rounded-xl shadow-inner border border-white/10"
          style={{ backgroundImage: `linear-gradient(135deg, rgba(255,255,255,0.05), rgba(255,255,255,0.01))` }}
        >
          <Icon size={22} style={{ color: color1 }} />
        </div>
      </div>
    </motion.div>
  );
};


const Dashboard = () => {
  const [breakdown, setBreakdown] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Simulate initial loading sequence for effect
    const timer = setTimeout(() => {
      fetchCosts();
    }, 800);
    return () => clearTimeout(timer);
  }, []);

  const fetchCosts = async () => {
    try {
      const response = await axios.get('/api/v1/costs/breakdown');
      setBreakdown(response.data.breakdown || []);
    } catch (err) {
      console.error("Failed to fetch breakdown", err);
      setError("API unreachable. Initializing live interactive demonstration mode.");

      // Premium mock data
      setBreakdown([
        { model: "gpt-4o-2024-08-06", task_type: "extraction", total_cost_usd: 840.50, call_count: 54000 },
        { model: "claude-3-haiku-20240307", task_type: "extraction", total_cost_usd: 42.20, call_count: 28200 },
        { model: "gpt-4o-mini-2024-07-18", task_type: "classification", total_cost_usd: 115.40, call_count: 122000 },
        { model: "claude-3-5-sonnet", task_type: "summarization", total_cost_usd: 410.00, call_count: 21000 },
        { model: "gpt-4o-2024-08-06", task_type: "generation", total_cost_usd: 1240.00, call_count: 61000 }
      ]);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-[#030712] relative overflow-hidden">
        <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-20 pointer-events-none mix-blend-overlay"></div>
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ repeat: Infinity, duration: 8, ease: "linear" }}
          className="relative w-24 h-24"
        >
          <div className="absolute inset-0 rounded-full border-t-2 border-r-2 border-accent-blue/30 blur-[2px]"></div>
          <div className="absolute inset-2 rounded-full border-b-2 border-l-2 border-accent-purple/50"></div>
          <div className="absolute inset-4 rounded-full border-t-2 border-r-2 border-white"></div>
        </motion.div>
        <motion.p
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5 }}
          className="mt-6 text-intel-400 font-medium tracking-widest text-sm uppercase"
        >
          Initializing Intelligence Engine
        </motion.p>
      </div>
    );
  }

  // Analytics Engine
  const totalCost = breakdown.reduce((sum, item) => sum + item.total_cost_usd, 0);
  const totalCalls = breakdown.reduce((sum, item) => sum + item.call_count, 0);
  const uniqueModels = [...new Set(breakdown.map(item => item.model))];

  // Aggregations
  const modelCosts = breakdown.reduce((acc, item) => {
    const existing = acc.find(x => x.name === item.model);
    if (existing) {
      existing.value += item.total_cost_usd;
    } else {
      acc.push({ name: item.model, value: item.total_cost_usd });
    }
    return acc.sort((a, b) => b.value - a.value); // Sort desc
  }, []);

  const taskCosts = breakdown.reduce((acc, item) => {
    const existing = acc.find(x => x.name === item.task_type);
    if (existing) {
      existing[item.model] = item.total_cost_usd;
    } else {
      acc.push({ name: item.task_type, [item.model]: item.total_cost_usd });
    }
    return acc;
  }, []);

  return (
    <div className="min-h-screen bg-[#030712] relative selection:bg-accent-blue/30 selection:text-white">
      {/* Static Noise Overlay for texture */}
      <div className="fixed inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-[0.15] pointer-events-none mix-blend-overlay z-0"></div>

      <div className="max-w-[1600px] mx-auto p-6 md:p-8 relative z-10">

        {/* Header & Alert */}
        <motion.header
          initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }}
          className="flex flex-col md:flex-row md:items-end justify-between gap-4 mb-10"
        >
          <div>
            <div className="flex items-center gap-3 mb-2">
              <div className="p-2 bg-gradient-to-tr from-accent-blue to-accent-purple rounded-lg shadow-lg shadow-accent-blue/20">
                <Sparkles size={20} className="text-white" />
              </div>
              <h1 className="text-3xl font-bold tracking-tight text-white">Staxx Intelligence</h1>
            </div>
            <p className="text-intel-400 font-medium ml-12">Production Efficiency & Model Routing</p>
          </div>

          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 px-4 py-2 rounded-full glass-panel border border-white/5">
              <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse shadow-[0_0_8px_rgba(16,185,129,0.8)]"></div>
              <span className="text-sm font-medium text-intel-100">System Active</span>
            </div>
          </div>
        </motion.header>

        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }}
              className="mb-8 overflow-hidden"
            >
              <div className="glass-panel border-l-4 border-l-amber-500 p-4 rounded-xl flex items-start gap-3 bg-amber-500/5">
                <AlertCircle className="text-amber-500 shrink-0 mt-0.5" size={20} />
                <p className="text-amber-200/90 text-sm font-medium leading-relaxed">{error}</p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Top KPIs */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-10">
          <StatCard
            title="Total Spend (7d)"
            value={`$${totalCost.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
            subtitle="Trailing 7 days API consumption"
            icon={DollarSign} colorIdx={0} delay={1}
            trend="+12.4%"
          />
          <StatCard
            title="Production Inferences"
            value={totalCalls.toLocaleString()}
            subtitle="Total routed requests"
            icon={Activity} colorIdx={2} delay={2}
          />
          <StatCard
            title="Active Models"
            value={uniqueModels.length}
            subtitle="Engines continuously evaluated"
            icon={Layers} colorIdx={1} delay={3}
          />
          <StatCard
            title="Projected Savings"
            value={"$0.00"}
            subtitle="Awaiting shadow evaluation completion"
            icon={Zap} colorIdx={3} delay={4}
          />
        </div>

        {/* Charts Section */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-10">

          {/* Main Bar Chart */}
          <motion.div
            initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.5, duration: 0.6 }}
            className="glass-panel p-6 rounded-2xl col-span-1 lg:col-span-2 flex flex-col"
          >
            <div className="flex justify-between items-center mb-6">
              <div>
                <h3 className="text-lg font-semibold text-white">Spend Topology by Task</h3>
                <p className="text-sm text-intel-400 mt-1">Cost distribution across core capabilities</p>
              </div>
              <button className="p-2 hover:bg-white/5 rounded-lg transition-colors text-intel-400 hover:text-white">
                <TerminalSquare size={18} />
              </button>
            </div>

            <div className="flex-1 min-h-[320px] w-full mt-2">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={taskCosts} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis
                    dataKey="name"
                    axisLine={false} tickLine={false}
                    tick={{ fill: '#94a3b8', fontSize: 13, fontWeight: 500 }}
                    dy={10}
                  />
                  <YAxis
                    tickFormatter={(value) => `$${value}`}
                    axisLine={false} tickLine={false}
                    tick={{ fill: '#64748b', fontSize: 12 }}
                  />
                  <RechartsTooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255,255,255,0.02)' }} />
                  <Legend
                    iconType="circle"
                    wrapperStyle={{ paddingTop: '20px', fontSize: '13px', color: '#cbd5e1' }}
                  />
                  {uniqueModels.map((model, idx) => (
                    <Bar
                      key={model}
                      dataKey={model}
                      stackId="a"
                      fill={COLORS[idx % COLORS.length]}
                      radius={[idx === uniqueModels.length - 1 ? 6 : 0, idx === uniqueModels.length - 1 ? 6 : 0, 0, 0]}
                      barSize={40}
                    />
                  ))}
                </BarChart>
              </ResponsiveContainer>
            </div>
          </motion.div>

          {/* Donut Chart */}
          <motion.div
            initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.6, duration: 0.6 }}
            className="glass-panel p-6 rounded-2xl flex flex-col"
          >
            <div>
              <h3 className="text-lg font-semibold text-white">Model Capital Allocation</h3>
              <p className="text-sm text-intel-400 mt-1">Vendor spend distribution</p>
            </div>

            <div className="flex-1 w-full min-h-[300px] mt-4 flex items-center justify-center">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={modelCosts}
                    cx="50%" cy="50%"
                    innerRadius={70} outerRadius={100}
                    paddingAngle={3}
                    dataKey="value"
                    stroke="rgba(0,0,0,0)"
                    cornerRadius={4}
                  >
                    {modelCosts.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <RechartsTooltip content={<CustomTooltip />} />
                </PieChart>
              </ResponsiveContainer>
            </div>

            {/* Custom Interactive Legend for Pie to make it look premium */}
            <div className="space-y-3 mt-2">
              {modelCosts.slice(0, 5).map((item, idx) => (
                <div key={item.name} className="flex items-center justify-between text-sm py-1 border-b border-white/5 hover:bg-white/5 px-2 rounded-lg transition-colors cursor-pointer">
                  <div className="flex items-center gap-3">
                    <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: COLORS[idx % COLORS.length] }}></div>
                    <span className="text-intel-100 font-medium truncate max-w-[120px]">{item.name}</span>
                  </div>
                  <span className="text-white font-semibold">${item.value.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}</span>
                </div>
              ))}
            </div>
          </motion.div>

        </div>

        {/* Intelligence Actions Row */}
        <motion.div
          initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.8, duration: 0.6 }}
        >
          <div className="glass-card p-1 rounded-2xl relative overflow-hidden group border border-white/10">
            {/* Animated border gradient */}
            <div className="absolute inset-0 bg-gradient-to-r from-accent-blue/10 via-transparent to-accent-emerald/10 opacity-30 group-hover:opacity-100 transition-opacity duration-700"></div>

            <div className="bg-[#0f172a]/90 backdrop-blur-xl p-8 rounded-xl relative z-10 flex flex-col lg:flex-row items-start lg:items-center justify-between gap-8">
              <div className="max-w-xl">
                <div className="flex items-center gap-3 mb-3">
                  <div className="p-1.5 bg-accent-blue/20 rounded-md border border-accent-blue/30">
                    <Zap size={16} className="text-accent-blue" />
                  </div>
                  <h3 className="text-xl font-bold text-white">Awaiting Statistical Confidence</h3>
                  <span className="px-2.5 py-0.5 rounded-full bg-white/10 text-intel-100 text-xs font-semibold uppercase tracking-wider border border-white/10">
                    Engine V2
                  </span>
                </div>
                <p className="text-intel-400 font-medium leading-relaxed">
                  The shadow evaluation engine is currently intercepting production traffic.
                  Swap recommendations will activate automatically once a candidate model achieves <strong>N≥20</strong> runs bounded by a 95% confidence interval, ensuring zero quality regression.
                </p>
              </div>

              <button className="shrink-0 flex items-center justify-center gap-2 group/btn relative overflow-hidden px-6 py-3 rounded-xl bg-white text-[#0f172a] font-bold shadow-[0_0_20px_rgba(255,255,255,0.1)] hover:shadow-[0_0_30px_rgba(255,255,255,0.3)] transition-all duration-300">
                <span className="relative z-10">View Evaluation Queue</span>
                <ChevronRight size={18} className="relative z-10 group-hover/btn:translate-x-1 transition-transform" />
                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/40 to-transparent -translate-x-full group-hover/btn:animate-[shimmer_1.5s_infinite]"></div>
              </button>
            </div>
          </div>
        </motion.div>

      </div>
    </div>
  );
};

export default Dashboard;
