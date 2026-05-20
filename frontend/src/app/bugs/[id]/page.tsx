"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { Header } from "@/components/layout/header";
import { BugDetailCard } from "@/components/bugs/bug-detail-card";
import { BugDialog } from "@/components/bugs/bug-dialog";
import { useBugsStore } from "@/store/bugs-store";
import { buttonVariants } from "@/components/ui/button";
import { ArrowLeft } from "lucide-react";
import { cn } from "@/lib/utils";
import { useEffect } from "react";

export default function BugDetailPage() {
  const params = useParams();
  const { bugs, fetchBugs } = useBugsStore();
  const bug = bugs.find(b => b.id === (params.id as string));

  useEffect(() => {
    if (bugs.length === 0) fetchBugs();
  }, [bugs.length, fetchBugs]);

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
    </>
  );
}
