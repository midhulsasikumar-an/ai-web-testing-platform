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

export default function BugDetailPage() {
  const params = useParams();
  const { getBugById } = useBugContext();
  const bug = getBugById(params.id as string);

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
