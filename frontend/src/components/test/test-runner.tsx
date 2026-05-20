"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { executionService } from "@/services/execution.service";
import { useExecutionStore } from "@/store/execution-store";
import { TestConfigForm } from "./test-config-form";
import { AIFindingsPanel } from "./ai-findings-panel";
import { Loader2 } from "lucide-react";

export function TestRunner() {
  const router = useRouter();
  const { startExecution } = useExecutionStore();
  
  const [url, setUrl] = useState("");
  const [githubUrl, setGithubUrl] = useState("");
  const [testType, setTestType] = useState<"full" | "ai" | "accessibility">("full");
  const [loading, setLoading] = useState(false);

  const handleRunTest = async () => {
    if (!url.trim()) return;
    setLoading(true);
    try {
      const response = await executionService.startTest(url, "Web App Test");
      startExecution(response.data.execution_id, url);
      router.push(`/execution/${response.data.execution_id}`);
    } catch (error) {
      console.error("Failed to start test:", error);
      alert("Failed to start test. Please ensure backend is running.");
      setLoading(false);
    }
  };

  return (
    <div className="grid gap-6 lg:grid-cols-5">
      {/* Left column: Config */}
      <div className="lg:col-span-3 space-y-6">
        <TestConfigForm
          url={url}
          onUrlChange={setUrl}
          githubUrl={githubUrl}
          onGithubUrlChange={setGithubUrl}
          testType={testType}
          onTestTypeChange={setTestType}
          loading={loading}
          onRunTest={handleRunTest}
        />
        
        {loading && (
          <div className="flex flex-col items-center justify-center p-12 bg-white rounded-lg border border-gray-200">
            <Loader2 className="w-8 h-8 text-blue-500 animate-spin mb-4" />
            <p className="text-gray-600 font-medium">Initializing Pipeline...</p>
          </div>
        )}
      </div>

      {/* Right column: Info */}
      <div className="lg:col-span-2 space-y-4">
        {/* Placeholder for now since aiFindings aren't populated here anymore */}
        <AIFindingsPanel findings={[]} />
      </div>
    </div>
  );
}
