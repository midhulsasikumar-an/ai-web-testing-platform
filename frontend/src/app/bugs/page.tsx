"use client";

import { Header } from "@/components/layout/header";
import { BugTable } from "@/components/bugs/bug-table";
import { useBugsStore } from "@/store/bugs-store";
import Link from "next/link";
import { buttonVariants } from "@/components/ui/button";
import { Play } from "lucide-react";
import { cn } from "@/lib/utils";
import { useEffect } from "react";

export default function BugsPage() {
  const { bugs, fetchBugs } = useBugsStore();

  useEffect(() => {
    fetchBugs();
  }, [fetchBugs]);

  return (
    <>
      <Header
        title="Bug Tracker"
        description={`${bugs.length} bug${bugs.length !== 1 ? "s" : ""} recorded across all test runs.`}
      >
        <Link href="/run-test" className={cn(buttonVariants({ size: "sm" }))}>
          <Play className="h-4 w-4 mr-2" />
          Run Test
        </Link>
      </Header>
      <BugTable bugs={bugs} />
    </>
  );
}
