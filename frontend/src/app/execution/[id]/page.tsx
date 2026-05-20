import { Header } from "@/components/layout/header";
import { ExecutionMonitor } from "@/components/execution/execution-monitor";
import { AILogsViewer } from "@/components/execution/ai-logs-viewer";
import { ScreenshotPreview } from "@/components/execution/screenshot-preview";

export default function ExecutionPage({ params }: { params: { id: string } }) {
  return (
    <>
      <Header
        title={`Execution Run: ${params.id}`}
        description="Live monitoring of automated QA pipeline."
      />
      
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-6">
        <div className="lg:col-span-2 space-y-6">
          <ExecutionMonitor executionId={params.id} />
          <AILogsViewer />
        </div>
        <div className="space-y-6">
          <ScreenshotPreview />
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h3 className="font-semibold text-gray-900 mb-4">Run Details</h3>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between border-b pb-2">
                <span className="text-gray-500">ID</span>
                <span className="font-mono text-gray-900">{params.id.slice(0, 8)}</span>
              </div>
              <div className="flex justify-between border-b pb-2">
                <span className="text-gray-500">Started</span>
                <span className="text-gray-900">Just now</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Environment</span>
                <span className="text-gray-900">Production</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
