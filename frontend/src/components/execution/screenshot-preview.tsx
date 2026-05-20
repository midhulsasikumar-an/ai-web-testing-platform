"use client";

import React from "react";
import { ImageIcon } from "lucide-react";
import { useExecutionStore } from "@/store/execution-store";

export function ScreenshotPreview() {
  const { status } = useExecutionStore();

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
      <h3 className="font-semibold text-gray-900 mb-4">Latest Screenshot</h3>
      
      <div className="aspect-video bg-gray-100 rounded border border-gray-200 flex items-center justify-center flex-col gap-2 overflow-hidden relative">
        {/* Mock screenshot based on status */}
        {status === "completed" ? (
          <div className="absolute inset-0 bg-blue-50 flex items-center justify-center text-blue-600 font-medium">
            Test Completed Successfully
          </div>
        ) : status === "failed" ? (
           <div className="absolute inset-0 bg-red-50 flex items-center justify-center text-red-600 font-medium">
            Crash detected in UI
          </div>
        ) : (
          <>
            <ImageIcon className="w-8 h-8 text-gray-400" />
            <span className="text-sm text-gray-500">Waiting for browser frame...</span>
          </>
        )}
      </div>
    </div>
  );
}
