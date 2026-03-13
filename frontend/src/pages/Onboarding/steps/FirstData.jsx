/**
 * Step 4: First Data - Wait for first LLM call, celebrate with confetti.
 */

import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { CheckCircle2, ArrowRight } from "lucide-react";
import { GlassPanel } from "../../../components/GlassPanel";

function Confetti() {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;

    const particles = [];
    const colors = ["#22c55e", "#0ea5e9", "#f59e0b", "#ec4899", "#8b5cf6"];

    // Create particles
    for (let i = 0; i < 60; i++) {
      particles.push({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height - canvas.height,
        vx: (Math.random() - 0.5) * 8,
        vy: Math.random() * 5 + 5,
        size: Math.random() * 4 + 2,
        color: colors[Math.floor(Math.random() * colors.length)],
        life: 1,
      });
    }

    let frameCount = 0;
    const maxFrames = 120; // 2 seconds at 60fps

    const animate = () => {
      if (frameCount >= maxFrames) {
        canvas.style.opacity = "0";
        canvas.style.pointerEvents = "none";
        return;
      }

      ctx.clearRect(0, 0, canvas.width, canvas.height);

      particles.forEach((p) => {
        p.x += p.vx;
        p.y += p.vy;
        p.vy += 0.2; // gravity
        p.life -= 1 / maxFrames;

        ctx.globalAlpha = p.life;
        ctx.fillStyle = p.color;
        ctx.fillRect(p.x, p.y, p.size, p.size);
      });

      frameCount++;
      requestAnimationFrame(animate);
    };

    animate();
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 pointer-events-none transition-opacity duration-500"
      style={{ zIndex: 50 }}
    />
  );
}

export function FirstData({ apiKey, onNext }) {
  const [eventData, setEventData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [celebration, setCelebration] = useState(false);
  const navigate = useNavigate();
  const pollIntervalRef = useRef(null);

  useEffect(() => {
    // Simulate receiving first event after 3 seconds (demo mode)
    const demoTimeout = setTimeout(() => {
      setCelebration(true);
      setEventData({
        model: "GPT-4o",
        input_tokens: 245,
        output_tokens: 87,
        cost_usd: 0.0245,
        task_type: "summarization",
      });
      setLoading(false);
    }, 3000);

    return () => clearTimeout(demoTimeout);
  }, []);

  const handleDashboard = () => {
    navigate("/");
  };

  return (
    <motion.div
      initial={{ opacity: 0, x: 40 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -40 }}
      transition={{ duration: 0.3 }}
      className="w-full max-w-md"
    >
      <AnimatePresence mode="wait">
        {loading ? (
          <motion.div
            key="waiting"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="text-center space-y-6"
          >
            <div className="space-y-3">
              <h2 className="text-2xl font-bold text-white">
                Waiting for your first event...
              </h2>
              <p className="text-sm text-zinc-400">
                Make an LLM API call using your Staxx integration
              </p>
            </div>

            {/* Pulsing Dots */}
            <div className="flex justify-center gap-2 py-8">
              {[0, 1, 2].map((i) => (
                <motion.div
                  key={i}
                  animate={{ scale: [1, 1.2, 1], opacity: [0.5, 1, 0.5] }}
                  transition={{
                    duration: 1.5,
                    repeat: Infinity,
                    delay: i * 0.2,
                  }}
                  className="w-3 h-3 rounded-full bg-green-500"
                />
              ))}
            </div>

            {/* Status Message */}
            <GlassPanel className="bg-zinc-800/30">
              <p className="text-xs text-zinc-400">
                This may take a few moments. Staxx is listening for incoming LLM traffic...
              </p>
            </GlassPanel>
          </motion.div>
        ) : (
          <motion.div
            key="success"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="space-y-6"
          >
            {/* Confetti */}
            {celebration && <Confetti />}

            {/* Success Header */}
            <div className="text-center space-y-3">
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ type: "spring", delay: 0.3 }}
              >
                <CheckCircle2
                  size={48}
                  className="text-green-400 mx-auto drop-shadow-lg"
                />
              </motion.div>
              <h2 className="text-2xl font-bold text-white">
                Your Dashboard is Ready!
              </h2>
              <p className="text-sm text-zinc-400">
                Staxx successfully captured your first LLM call
              </p>
            </div>

            {/* Event Details Card */}
            {eventData && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5 }}
              >
                <GlassPanel className="bg-green-500/5 border-green-500/20">
                  <div className="space-y-3">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <p className="text-xs text-zinc-400 mb-1">Model</p>
                        <p className="text-sm font-semibold text-white">
                          {eventData.model}
                        </p>
                      </div>
                      <div>
                        <p className="text-xs text-zinc-400 mb-1">Task Type</p>
                        <p className="text-sm font-semibold text-white capitalize">
                          {eventData.task_type}
                        </p>
                      </div>
                      <div>
                        <p className="text-xs text-zinc-400 mb-1">Input Tokens</p>
                        <p className="text-sm font-semibold text-white">
                          {eventData.input_tokens}
                        </p>
                      </div>
                      <div>
                        <p className="text-xs text-zinc-400 mb-1">Cost</p>
                        <p className="text-sm font-semibold text-green-400">
                          ${eventData.cost_usd.toFixed(4)}
                        </p>
                      </div>
                    </div>
                  </div>
                </GlassPanel>
              </motion.div>
            )}

            {/* Call to Action */}
            <motion.button
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.7 }}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={handleDashboard}
              className="w-full py-3 rounded-lg bg-gradient-to-r from-green-500 to-sky-500
                hover:from-green-600 hover:to-sky-600 text-white font-semibold
                transition-all flex items-center justify-center gap-2 shadow-lg
                shadow-green-500/20"
            >
              Go to Dashboard
              <ArrowRight size={18} />
            </motion.button>

            {/* Footer Message */}
            <p className="text-xs text-center text-zinc-500">
              You're all set! Start optimizing your LLM costs with Staxx.
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
