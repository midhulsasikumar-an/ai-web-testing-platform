"use client";

import { Header } from "@/components/layout/header";
import { BugTable } from "@/components/bugs/bug-table";
import { useBugContext } from "@/context/bug-context";

export default function BugsPage() {
  const { bugs } = useBugContext();

  return (
    <>
      <Header
        title="Bug Tracker"
        description="Monitor bugs discovered across all tested websites and applications."
      />
      <BugTable bugs={bugs} />
    </>
  );
}
