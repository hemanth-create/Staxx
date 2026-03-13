/**
 * Step 1: Create Account - Email, password, company name signup.
 */

import { useState } from "react";
import { motion } from "framer-motion";
import { Mail, Lock, Building2, AlertCircle } from "lucide-react";
import axios from "axios";
import { GlassPanel } from "../../../components/GlassPanel";

export function CreateAccount({ onNext }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const response = await axios.post("/api/v1/onboarding/signup", {
        email,
        password,
        company_name: companyName,
      });

      const { token, api_key, org_id, proxy_url } = response.data;

      onNext({
        email,
        token,
        apiKey: api_key,
        orgId: org_id,
        proxyUrl: proxy_url,
      });
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          "Failed to create account. Please try again."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, x: 40 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -40 }}
      transition={{ duration: 0.3 }}
      className="w-full max-w-md"
    >
      <GlassPanel>
        <div className="space-y-6">
          {/* Header */}
          <div className="text-center">
            <h2 className="text-2xl font-bold text-white mb-2">
              Create Your Account
            </h2>
            <p className="text-sm text-zinc-400">
              Join Staxx and start optimizing your LLM costs
            </p>
          </div>

          {/* Error Alert */}
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="p-4 rounded-lg bg-red-500/10 border border-red-500/30 flex gap-3"
            >
              <AlertCircle size={18} className="text-red-400 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-red-300">{error}</p>
            </motion.div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Email Input */}
            <div>
              <label className="block text-sm font-medium text-zinc-300 mb-2">
                Email Address
              </label>
              <div className="relative">
                <Mail
                  size={18}
                  className="absolute left-3 top-3 text-zinc-500 pointer-events-none"
                />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@company.com"
                  required
                  className="w-full pl-10 pr-4 py-2.5 rounded-lg bg-zinc-800/50 border border-zinc-700
                    text-white placeholder-zinc-500 focus:outline-none focus:border-sky-500/50
                    transition-colors"
                />
              </div>
            </div>

            {/* Password Input */}
            <div>
              <label className="block text-sm font-medium text-zinc-300 mb-2">
                Password
              </label>
              <div className="relative">
                <Lock
                  size={18}
                  className="absolute left-3 top-3 text-zinc-500 pointer-events-none"
                />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="At least 8 characters"
                  minLength={8}
                  required
                  className="w-full pl-10 pr-4 py-2.5 rounded-lg bg-zinc-800/50 border border-zinc-700
                    text-white placeholder-zinc-500 focus:outline-none focus:border-sky-500/50
                    transition-colors"
                />
              </div>
            </div>

            {/* Company Name Input */}
            <div>
              <label className="block text-sm font-medium text-zinc-300 mb-2">
                Company Name
              </label>
              <div className="relative">
                <Building2
                  size={18}
                  className="absolute left-3 top-3 text-zinc-500 pointer-events-none"
                />
                <input
                  type="text"
                  value={companyName}
                  onChange={(e) => setCompanyName(e.target.value)}
                  placeholder="Acme Corp"
                  required
                  className="w-full pl-10 pr-4 py-2.5 rounded-lg bg-zinc-800/50 border border-zinc-700
                    text-white placeholder-zinc-500 focus:outline-none focus:border-sky-500/50
                    transition-colors"
                />
              </div>
            </div>

            {/* Submit Button */}
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              type="submit"
              disabled={loading}
              className="w-full py-2.5 rounded-lg bg-green-500 hover:bg-green-600 disabled:bg-zinc-600
                text-white font-semibold transition-all duration-200 flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <motion.div
                    animate={{ rotate: 360 }}
                    transition={{ repeat: Infinity, duration: 1 }}
                  >
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full" />
                  </motion.div>
                  Creating...
                </>
              ) : (
                "Create Account →"
              )}
            </motion.button>
          </form>

          {/* Divider */}
          <div className="relative py-4">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-zinc-700" />
            </div>
            <div className="relative flex justify-center text-xs">
              <span className="px-2 bg-zinc-900 text-zinc-500">or</span>
            </div>
          </div>

          {/* OAuth Button (Placeholder) */}
          <button
            disabled
            className="w-full py-2.5 rounded-lg border border-zinc-700 text-zinc-400
              font-medium bg-zinc-800/20 cursor-not-allowed opacity-50"
          >
            Continue with Google
          </button>

          {/* Footer */}
          <p className="text-xs text-center text-zinc-500">
            By signing up, you agree to our{" "}
            <span className="text-zinc-400 hover:text-zinc-300">Terms of Service</span>
          </p>
        </div>
      </GlassPanel>
    </motion.div>
  );
}
