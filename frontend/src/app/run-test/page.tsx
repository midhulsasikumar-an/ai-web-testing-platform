"use client";

import { Header } from "@/components/layout/header";
import { TestRunner } from "@/components/test/test-runner";

export default function RunTestPage() {
  return (
    <>
      <Header
        title="Run New Test"
        description="Deploy AI-powered probes to test, scan, and validate your applications."
      />
      <TestRunner />
    </>
  );
}
