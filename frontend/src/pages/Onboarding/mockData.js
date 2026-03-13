/**
 * Onboarding mock data: integration methods and code snippets.
 */

import { Globe, Code2, Cloud } from "lucide-react";

export const integrationMethods = [
  {
    id: "proxy",
    name: "Proxy Gateway",
    icon: Globe,
    description: "Change one URL, see data instantly",
    setupTime: "2 minutes",
    complexity: "Easy",
    badge: "Recommended",
    badgeColor: "bg-green-500/20 border-green-500/50",
  },
  {
    id: "sdk",
    name: "SDK Drop-in",
    icon: Code2,
    description: "Add 2 lines of Python/JS code",
    setupTime: "5 minutes",
    complexity: "Easy",
    badge: "Flexible",
    badgeColor: "bg-blue-500/20 border-blue-500/50",
  },
  {
    id: "log_connector",
    name: "Log Connector",
    icon: Cloud,
    description: "Connect CloudWatch, Datadog, or LangSmith",
    setupTime: "10 minutes",
    complexity: "Advanced",
    badge: "Enterprise",
    badgeColor: "bg-purple-500/20 border-purple-500/50",
  },
];

export const codeSnippets = {
  proxy: {
    label: "Environment Variable",
    language: "bash",
    envVar: `export OPENAI_BASE_URL="https://proxy.staxx.ai/v1"
# Then use your normal OpenAI SDK as usual`,
    pythonBefore: `from openai import OpenAI
client = OpenAI(api_key="sk-...")`,
    pythonAfter: `from openai import OpenAI
client = OpenAI(
    api_key="sk-...",
    base_url="https://proxy.staxx.ai/v1"
)`,
  },
  sdk: {
    pip: "pip install staxx-intelligence",
    python: `from staxx import StaxxClient
client = StaxxClient(api_key="{API_KEY}")

# That's it! All LLM calls are automatically tracked`,
  },
  log_connector: {
    instructions: [
      "1. Go to AWS IAM → Create a new role for Staxx",
      "2. Attach policy: CloudWatch Logs read access",
      "3. Copy the role ARN and paste below",
      "4. Staxx will poll your CloudWatch logs every 5 minutes",
    ],
    defaultArn: "arn:aws:iam::ACCOUNT-ID:role/StaxxLogReader",
  },
};

export const stepLabels = [
  "Create Account",
  "Choose Integration",
  "Set Up Connection",
  "Verify Data",
];
