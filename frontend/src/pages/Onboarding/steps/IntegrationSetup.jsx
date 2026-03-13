/**
 * Step 3: Integration Setup - Dynamic setup based on integration method.
 */

import { useState } from "react";
import { motion } from "framer-motion";
import axios from "axios";
import { GlassPanel } from "../../../components/GlassPanel";
import { CodeSnippet } from "../components/CodeSnippet";
import { ConnectionStatus } from "../components/ConnectionStatus";
import { codeSnippets } from "../mockData";

export function IntegrationSetup({ integrationMethod, apiKey, proxyUrl, onNext }) {
  const [connectionStatus, setConnectionStatus] = useState("idle");
  const [awsAccountId, setAwsAccountId] = useState("");
  const [error, setError] = useState("");

  const handleTestConnection = async () => {
    setConnectionStatus("checking");
    setError("");

    try {
      const response = await axios.post("/api/v1/onboarding/test-connection", {
        integration_type: integrationMethod,
        api_key: apiKey,
      });

      if (response.data.status === "connected") {
        setConnectionStatus("connected");
        setTimeout(() => {
          onNext({ connectionTested: true });
        }, 1000);
      } else {
        setConnectionStatus("failed");
        setError(response.data.message || "Connection failed. Please try again.");
      }
    } catch (err) {
      setConnectionStatus("failed");
      setError(
        err.response?.data?.detail ||
          "Connection test failed. Please check your API key."
      );
    }
  };

  const renderMethodSetup = () => {
    switch (integrationMethod) {
      case "proxy":
        return (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-bold text-white mb-3">
                1. Update Your Environment Variable
              </h3>
              <CodeSnippet
                code={codeSnippets.proxy.envVar}
                language="bash"
                label="Environment Variable"
              />
            </div>

            <div>
              <h3 className="text-lg font-bold text-white mb-3">
                2. Proxy URL
              </h3>
              <GlassPanel className="bg-green-500/5 border-green-500/20">
                <div className="space-y-2">
                  <p className="text-sm text-zinc-300">Use this proxy URL:</p>
                  <code className="block text-sm font-mono text-green-400 break-all">
                    {proxyUrl}
                  </code>
                  <p className="text-xs text-zinc-400 mt-3">
                    Replace your current OpenAI base URL with this one. The proxy will
                    intercept all requests and log them to Staxx.
                  </p>
                </div>
              </GlassPanel>
            </div>

            <div>
              <h3 className="text-lg font-bold text-white mb-3">3. Test Connection</h3>
              <ConnectionStatus status={connectionStatus} label="Proxy Gateway" />
            </div>
          </div>
        );

      case "sdk":
        return (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-bold text-white mb-3">
                1. Install the SDK
              </h3>
              <CodeSnippet
                code={codeSnippets.sdk.pip}
                language="bash"
                label="Install Command"
              />
            </div>

            <div>
              <h3 className="text-lg font-bold text-white mb-3">
                2. Add 2 Lines of Code
              </h3>
              <CodeSnippet
                code={codeSnippets.sdk.python.replace("{API_KEY}", apiKey || "YOUR_API_KEY")}
                language="python"
                label="Python Code"
              />
            </div>

            <div>
              <h3 className="text-lg font-bold text-white mb-3">3. Send Test Event</h3>
              <ConnectionStatus status={connectionStatus} label="SDK Drop-in" />
            </div>
          </div>
        );

      case "log_connector":
        return (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-bold text-white mb-3">
                1. Create IAM Role
              </h3>
              <div className="space-y-3">
                {codeSnippets.log_connector.instructions.map((instruction, idx) => (
                  <p key={idx} className="text-sm text-zinc-300">
                    {instruction}
                  </p>
                ))}
              </div>
            </div>

            <div>
              <h3 className="text-lg font-bold text-white mb-3">
                2. Enter AWS Account ID
              </h3>
              <input
                type="text"
                value={awsAccountId}
                onChange={(e) => setAwsAccountId(e.target.value)}
                placeholder="123456789012"
                className="w-full px-4 py-2.5 rounded-lg bg-zinc-800/50 border border-zinc-700
                  text-white placeholder-zinc-500 focus:outline-none focus:border-sky-500/50
                  font-mono"
              />
              <p className="text-xs text-zinc-400 mt-2">
                Your AWS Account ID (12 digits)
              </p>
            </div>

            <div>
              <h3 className="text-lg font-bold text-white mb-3">
                3. Verify Connection
              </h3>
              <ConnectionStatus status={connectionStatus} label="Log Connector" />
            </div>
          </div>
        );

      default:
        return null;
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
        <div>
          <h2 className="text-2xl font-bold text-white mb-2">Set Up Your Connection</h2>
          <p className="text-sm text-zinc-400">
            Follow the steps below to connect your LLM infrastructure
          </p>
        </div>

        {/* Error Alert */}
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="p-4 rounded-lg bg-red-500/10 border border-red-500/30 text-sm text-red-300"
          >
            {error}
          </motion.div>
        )}

        {/* Method-Specific Setup */}
        <GlassPanel>{renderMethodSetup()}</GlassPanel>

        {/* Action Buttons */}
        {connectionStatus !== "connected" && (
          <div className="flex gap-4">
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={handleTestConnection}
              disabled={connectionStatus === "checking"}
              className="flex-1 py-3 rounded-lg bg-sky-500 hover:bg-sky-600 disabled:bg-zinc-700
                text-white font-semibold transition-all flex items-center justify-center gap-2"
            >
              {connectionStatus === "checking" ? (
                <>
                  <motion.div
                    animate={{ rotate: 360 }}
                    transition={{ repeat: Infinity, duration: 1 }}
                  >
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full" />
                  </motion.div>
                  Testing...
                </>
              ) : (
                "Test Connection"
              )}
            </motion.button>
          </div>
        )}

        {connectionStatus === "connected" && (
          <motion.button
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => onNext({ connectionTested: true })}
            className="w-full py-3 rounded-lg bg-green-500 hover:bg-green-600
              text-white font-semibold transition-all"
          >
            Continue to Verification →
          </motion.button>
        )}
      </div>
    </motion.div>
  );
}
