/**
 * CodeSnippet - Styled code block with copy functionality.
 */

import { useState } from "react";
import { Copy, Check } from "lucide-react";

export function CodeSnippet({ code, language = "bash", label = null }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  return (
    <div className="relative bg-zinc-900 border border-zinc-700 rounded-lg overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-zinc-800/50 border-b border-zinc-700">
        {label && (
          <span className="text-xs font-semibold text-sky-400 uppercase tracking-wide">
            {label}
          </span>
        )}
        {language && !label && (
          <span className="text-xs font-mono text-zinc-500">{language}</span>
        )}
        <button
          onClick={handleCopy}
          className="ml-auto flex items-center gap-2 px-3 py-1 rounded-md
            bg-zinc-700/50 hover:bg-zinc-600 transition-colors
            text-zinc-300 text-xs font-medium"
        >
          {copied ? (
            <>
              <Check size={14} />
              <span>Copied!</span>
            </>
          ) : (
            <>
              <Copy size={14} />
              <span>Copy</span>
            </>
          )}
        </button>
      </div>

      {/* Code */}
      <pre className="px-4 py-4 overflow-x-auto">
        <code className="text-sm text-zinc-300 font-mono leading-relaxed whitespace-pre-wrap break-words">
          {code}
        </code>
      </pre>
    </div>
  );
}
