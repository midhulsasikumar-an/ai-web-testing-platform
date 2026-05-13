"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { Header } from "@/components/layout/header";
import { BugDetailCard } from "@/components/bugs/bug-detail-card";
import { BugDialog } from "@/components/bugs/bug-dialog";
import { useBugContext } from "@/context/bug-context";
import { buttonVariants } from "@/components/ui/button";
import { ArrowLeft } from "lucide-react";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function BugDetailPage() {
  const params = useParams();
  const { getBugById, getTestById } = useBugContext();
  const bug = getBugById(params.id as string);
  const linkedTest = bug?.test_id
    ? getTestById(bug.test_id)
    : null;

  if (!bug) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] gap-4">
        <p className="text-muted-foreground">Bug not found.</p>
        <Link href="/bugs" className={cn(buttonVariants({ variant: "outline" }))}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Bugs
        </Link>
      </div>
    );
  }

  return (
    <>
      <Header title="Bug Details">
        <Link href="/bugs" className={cn(buttonVariants({ variant: "outline", size: "sm" }))}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back
        </Link>
        <BugDialog bug={bug} />
      </Header>
      <BugDetailCard bug={bug} />

      {linkedTest && (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-semibold">
            Linked Test Run
          </CardTitle>
        </CardHeader>

        <CardContent>
          <Link
            href={`/test-history/${linkedTest.test_id}`}
            className="text-sm text-primary hover:underline"
          >
            View Original Test Run →
          </Link>
        </CardContent>
      </Card>
    )}
    </>
  );
}
