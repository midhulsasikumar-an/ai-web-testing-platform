"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { Header } from "@/components/layout/header";
import { useBugContext } from "@/context/bug-context";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { buttonVariants } from "@/components/ui/button";
import { formatDateLong, formatTime } from "@/lib/formatters";
import { MetadataField } from "@/components/shared/metadata-field";
import { TEST_TYPE_CONFIG } from "@/lib/constants";
import { cn } from "@/lib/utils";
import { API_BASE_URL } from "@/services/http";
import {
  ArrowLeft, CheckCircle2, XCircle, Globe,
  Clock, Terminal, ExternalLink, Play,
  Calendar,AlertTriangle,
  Sparkles,ShieldAlert,Lightbulb,
} from "lucide-react";


export default function TestDetailPage() {
  const params = useParams();
  const { getTestById } = useBugContext();
  const test = getTestById(params.id as string);
  const screenshotUrl = (path: string) => `${API_BASE_URL}${path}`;

  if (!test) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] gap-4">
        <Terminal className="h-10 w-10 text-muted-foreground/30" />
        <p className="text-muted-foreground font-medium">Test not found.</p>
        <Link href="/test-history" className={cn(buttonVariants({ variant: "outline" }))}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to History
        </Link>
      </div>
    );
  }

  const typeConfig = TEST_TYPE_CONFIG[test.test_type || "full"];
  const TypeIcon = typeConfig.icon;

  return (
    <>
      <Header title="Test Log Details">
        <Link href="/test-history" className={cn(buttonVariants({ variant: "outline", size: "sm" }))}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back
        </Link>
        <Link href="/run-test" className={cn(buttonVariants({ size: "sm" }))}>
          <Play className="h-4 w-4 mr-2" />
          Re-run
        </Link>
      </Header>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Main content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Result banner */}
          <Card className={
            test.overall_status === "pass"
              ? "border-green-500/30 bg-gradient-to-r from-green-50/50 to-transparent"
              : test.overall_status === "warning"
              ? "border-yellow-500/30 bg-gradient-to-r from-yellow-50/50 to-transparent"
              : "border-red-500/30 bg-gradient-to-r from-red-50/50 to-transparent"
          }>
            <CardContent className="pt-6">
              <div className="flex items-start gap-4">
                <div className={`flex h-12 w-12 items-center justify-center rounded-xl shrink-0 ${
                  test.overall_status === "pass" ? "bg-green-100" : "bg-red-100"
                }`}>
                  {test.overall_status === "pass" ? (
                    <CheckCircle2 className="h-6 w-6 text-green-600" />
                  ) : test.overall_status === "warning" ? (
                    <AlertTriangle className="h-6 w-6 text-yellow-500" />
                  ) : (
                    <XCircle className="h-6 w-6 text-red-600" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h2 className="text-xl font-bold">
                      {test.overall_status === "pass"
                        ? "Test Passed"
                        : test.overall_status === "warning"
                        ? "Test Warning"
                        : "Test Failed"}
                    </h2>
                    <Badge variant={test.overall_status === "pass" ? "secondary" : "destructive"}>
                      {test.overall_status}
                    </Badge>
                  </div>
                  <div className="mt-3 rounded-lg border border-border bg-background/60 p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <Sparkles className="h-4 w-4 text-primary" />
                      <p className="text-sm font-semibold">AI Executive Summary</p>
                    </div>

                    <p className="text-sm text-muted-foreground leading-relaxed">
                      {test.ai_summary || "No AI summary available"}
                    </p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Test Results</CardTitle>
            </CardHeader>

            <CardContent className="space-y-3">
              {test.results?.map((result, index) => (
                <div
                  key={index}
                  className="flex items-start justify-between border rounded-lg p-3"
                >
                  <div>
                    <p className="font-medium">{result.test}</p>

                    {result.details && (
                      <p className="text-sm text-muted-foreground">
                        {typeof result.details === "string"
                          ? result.details
                          : JSON.stringify(result.details)}
                      </p>
                    )}
                  </div>

                  <Badge
                    variant={
                      result.status === "pass"
                        ? "secondary"
                        : result.status === "fail"
                        ? "destructive"
                        : "outline"
                    }
                  >
                    {result.status}
                  </Badge>
                </div>
              ))}
            </CardContent>
          </Card>
          {/* Priority Issues */}
          {test.priority_issues && test.priority_issues.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <ShieldAlert className="h-5 w-5 text-red-500" />
                  Priority Issues
                </CardTitle>
              </CardHeader>

              <CardContent className="space-y-3">
                {test.priority_issues.map((issue, index) => (
                  <div
                    key={index}
                    className="rounded-lg border border-border p-4 bg-muted/20"
                  >
                    <div className="flex items-center justify-between">
                      <p className="font-medium">{issue.issue}</p>

                      <Badge
                        variant={
                          issue.level === "critical"
                            ? "destructive"
                            : issue.level === "moderate"
                            ? "outline"
                            : "secondary"
                        }
                      >
                        {issue.level}
                      </Badge>
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {/* Recommendations */}
          {test.recommendations && test.recommendations.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Lightbulb className="h-5 w-5 text-yellow-500" />
                  AI Recommendations
                </CardTitle>
              </CardHeader>

              <CardContent className="space-y-3">
                {test.recommendations.map((recommendation, index) => (
                  <div
                    key={index}
                    className="rounded-lg border border-border p-4 bg-muted/20"
                  >
                    <p className="text-sm leading-relaxed">
                      {recommendation}
                    </p>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}
        </div>

        {/* Right sidebar — Metadata */}
        <div className="space-y-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-semibold">Test Metadata</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <MetadataField icon={Terminal} label="Test ID">
                <p className="text-sm font-mono font-medium">{test.test_id}</p>
              </MetadataField>

              <MetadataField icon={Globe} label="Target URL">
                <a href={test.url} target="_blank" rel="noopener noreferrer" className="text-xs text-primary hover:underline flex items-center gap-1 break-all">
                  {test.url}
                  <ExternalLink className="h-3 w-3 shrink-0" />
                </a>
              </MetadataField>

              <MetadataField icon={TypeIcon} label="Test Type">
                <div className="flex items-center gap-1.5">
                  <TypeIcon className="h-3.5 w-3.5 text-primary" />
                  <span className="text-sm font-medium">{typeConfig.label}</span>
                </div>
              </MetadataField>

              <MetadataField icon={Clock} label="Health Score">
                <p className="text-sm font-mono font-medium">
                  {test.health_score || 0}/100
                </p>
              </MetadataField>

              <MetadataField icon={Calendar} label="Timestamp">
                <div className="text-sm">
                  <p>{formatDateLong(test.created_at || "")}</p>
                  <p className="text-xs text-muted-foreground">{formatTime(test.created_at || "")}</p>
                </div>
              </MetadataField>

              <MetadataField icon={test.overall_status === "pass" ? CheckCircle2 : XCircle} label="Result">
                <Badge variant={test.overall_status === "pass" ? "secondary" : "destructive"}>
                  {test.overall_status}
                </Badge>
              </MetadataField>
            </CardContent>
          </Card>
          {/* AI Report */}
          {test.report && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-semibold flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 text-primary" />
                  AI Detailed Report
                </CardTitle>
              </CardHeader>

              <CardContent>
                <div className="rounded-lg border border-border bg-muted/20 p-4">
                  <p className="text-sm leading-relaxed whitespace-pre-line text-muted-foreground">
                    {test.report}
                  </p>
                </div>
              </CardContent>
            </Card>
          )}
          {test.screenshot?.home && (
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-semibold">
                Homepage Screenshot
              </CardTitle>
            </CardHeader>

            <CardContent>
              <a
                href={screenshotUrl(test.screenshot.home)}
                target="_blank"
                rel="noopener noreferrer"
              >
                <img
                  src={screenshotUrl(test.screenshot.home)}
                  alt="Homepage Screenshot"
                  className="rounded-lg border border-border hover:opacity-90 transition"
                />
              </a>
            </CardContent>
          </Card>
        )}
        {test.screenshot?.button_interactions?.length && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold">
              Button Interaction Screenshots
            </CardTitle>
          </CardHeader>

          <CardContent className="space-y-4">
            {test.screenshot.button_interactions.map((img, index) => (
              <a
                key={index}
                href={screenshotUrl(img)}
                target="_blank"
                rel="noopener noreferrer"
              >
                <img
                  src={screenshotUrl(img)}
                  alt={`Interaction ${index + 1}`}
                  className="rounded-lg border border-border hover:opacity-90 transition"
                />
              </a>
            ))}
          </CardContent>
        </Card>
        )}
        </div>
      </div>
    </>
  );
}
