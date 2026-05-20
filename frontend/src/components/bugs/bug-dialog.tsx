"use client";

import { useState } from "react";
import type { Bug, BugStatus } from "@/types";
import { SeverityBadge } from "@/components/shared/severity-badge";
import {
  Dialog, DialogContent, DialogDescription, DialogHeader,
  DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import { statusColor } from "@/lib/constants";
import { useBugsStore } from "@/store/bugs-store";

interface BugDialogProps {
  bug: Bug;
}

const allStatuses: BugStatus[] = ["open", "in-progress", "resolved", "closed"];

export function BugDialog({ bug }: BugDialogProps) {
  const { updateBugStatus } = useBugsStore();
  const [open, setOpen] = useState(false);
  const [selectedStatus, setSelectedStatus] = useState<BugStatus>(bug.status);

  function handleSave() {
    updateBugStatus(bug.id, selectedStatus);
    setOpen(false);
  }

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="inline-flex h-7 items-center justify-center rounded-lg border border-border bg-background px-2.5 text-[0.8rem] font-medium hover:bg-muted transition-colors"
      >
        Edit Status
      </button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Update Bug Status</DialogTitle>
            <DialogDescription>{bug.id} — {bug.title}</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium w-20">Severity:</span>
              <SeverityBadge severity={bug.severity} />
            </div>
            <div className="space-y-2">
              <span className="text-sm font-medium">Status:</span>
              <div className="flex flex-wrap gap-2">
                {allStatuses.map((s) => (
                  <button key={s} onClick={() => setSelectedStatus(s)}
                    className={`px-3 py-1.5 rounded-md text-xs font-medium border transition-all ${
                      selectedStatus === s ? "ring-2 ring-primary ring-offset-2 ring-offset-background" : ""
                    } ${statusColor(s)}`}
                  >{s}</button>
                ))}
              </div>
            </div>
          </div>
          <DialogFooter>
            <button
              onClick={() => setOpen(false)}
              className="inline-flex h-8 items-center justify-center rounded-lg px-2.5 text-sm font-medium hover:bg-muted transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              className="inline-flex h-8 items-center justify-center rounded-lg bg-primary text-primary-foreground px-2.5 text-sm font-medium hover:bg-primary/80 transition-colors"
            >
              Save
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
