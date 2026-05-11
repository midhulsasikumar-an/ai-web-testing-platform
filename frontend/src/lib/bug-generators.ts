import type { Bug } from "@/types";
import type { TestApiResponse } from "@/services/test-api";

export function generateBugsFromTests(
  tests: TestApiResponse[]
): Bug[] {
  return tests
    .filter(
      (test) =>
        test.overall_status === "fail" ||
        test.overall_status === "warning"
    )
    .map((test, index) => ({
      id: `BUG-${index + 1}`,

      title:
        test.ai_summary || "Website issue detected",

      description:
        test.report || "AI detected issues during testing.",

      severity:
        test.overall_status === "fail"
          ? "high"
          : "medium",

      status: "open",

      url: test.url,

      createdAt:
        test.created_at || new Date().toISOString(),

      steps: test.results?.map(
        (r) => `${r.test}: ${r.details || r.status}`
      ) || [],

      assignedTo: "AI System",
    }));
}