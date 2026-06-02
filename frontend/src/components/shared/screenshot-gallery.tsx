"use client";

import { useEffect, useMemo, useState } from "react";
import { ChevronLeft, ChevronRight, Maximize2, Minus, Plus, X } from "lucide-react";

import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export type ScreenshotItem = {
  label: string;
  url: string;
  context?: string;
  bugId?: string;
};

type ScreenshotGalleryProps = {
  items: ScreenshotItem[];
  title?: string;
  description?: string;
  className?: string;
  gridClassName?: string;
  emptyText?: string;
  compact?: boolean;
  initialVisibleCount?: number;
  loadMoreStep?: number;
  maxBodyClassName?: string;
  showHeader?: boolean;
};

export function ScreenshotGallery({
  items,
  title = "Screenshot Gallery",
  description,
  className,
  gridClassName,
  emptyText = "No screenshots captured yet.",
  compact = false,
  initialVisibleCount = 12,
  loadMoreStep = 12,
  maxBodyClassName,
  showHeader = true,
}: ScreenshotGalleryProps) {
  const [previewIndex, setPreviewIndex] = useState<number | null>(null);
  const [visibleCount, setVisibleCount] = useState(initialVisibleCount);
  const [zoom, setZoom] = useState(1);

  const visibleItems = useMemo(() => items.slice(0, visibleCount), [items, visibleCount]);
  const previewItem = previewIndex !== null ? items[previewIndex] ?? null : null;
  const canLoadMore = visibleCount < items.length;

  useEffect(() => {
    if (previewIndex === null || typeof window === "undefined") {
      return;
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setPreviewIndex(null);
        return;
      }

      if (event.key === "ArrowRight") {
        setPreviewIndex((current) => (current === null ? current : (current + 1) % items.length));
        return;
      }

      if (event.key === "ArrowLeft") {
        setPreviewIndex((current) => (current === null ? current : (current - 1 + items.length) % items.length));
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [items.length, previewIndex]);

  useEffect(() => {
    setZoom(1);
  }, [previewIndex]);

  return (
    <section className={cn("rounded-xl border border-border bg-card text-sm text-card-foreground shadow-xs-token", className)}>
      {showHeader ? (
        <div className={cn("flex items-start justify-between gap-3 border-b border-border bg-white px-4 py-3", compact && "sticky top-0 z-10") }>
          <div className="min-w-0">
            <h2 className="truncate text-h3 text-slate-900">{title}</h2>
            {description ? <p className="mt-1 text-muted-sm">{description}</p> : null}
          </div>
        </div>
      ) : null}

      <div className={cn("p-4", compact && "p-3", maxBodyClassName)}>
        {items.length > 0 ? (
          <>
            <div className={cn("grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4", gridClassName)}>
              {visibleItems.map((shot, index) => (
                <button
                  key={`${shot.url}-${index}`}
                  type="button"
                  className="group overflow-hidden rounded-lg border border-border bg-slate-50 text-left transition-colors hover:border-primary/40 hover:bg-white"
                  onClick={() => setPreviewIndex(index)}
                >
                  <div className="aspect-[4/3] overflow-hidden bg-slate-100">
                    <img
                      src={shot.url}
                      alt={shot.label}
                      loading="lazy"
                      decoding="async"
                      className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-[1.03]"
                    />
                  </div>
                  <div className="flex items-center justify-between gap-2 px-3 py-2 border-t border-border">
                    <div className="min-w-0">
                      <span className="block truncate text-xs font-medium text-slate-700">{shot.label}</span>
                      {shot.context ? <span className="block truncate text-[10px] text-slate-500">{shot.context}</span> : null}
                    </div>
                    <Maximize2 className="h-3.5 w-3.5 shrink-0 text-slate-400" />
                  </div>
                </button>
              ))}
            </div>

            {canLoadMore ? (
              <div className="mt-3 flex justify-center">
                <button
                  type="button"
                  className={cn(buttonVariants({ variant: "outline", size: "sm" }))}
                  onClick={() => setVisibleCount((current) => Math.min(items.length, current + loadMoreStep))}
                >
                  Show more ({items.length - visibleCount})
                </button>
              </div>
            ) : null}
          </>
        ) : (
          <div className="rounded-lg border border-dashed border-border bg-slate-50 p-6 text-sm text-slate-500">
            {emptyText}
          </div>
        )}
      </div>

        {previewItem ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4" onClick={() => setPreviewIndex(null)}>
          <div className="relative w-full max-w-6xl overflow-hidden rounded-xl bg-white shadow-2xl" onClick={(event) => event.stopPropagation()}>
            <div className="flex items-center justify-between border-b border-border px-4 py-3">
              <div>
                <p className="text-sm font-semibold text-slate-900">Screenshot Preview</p>
                <p className="text-xs text-slate-500">{previewItem.label}{previewItem.context ? ` · ${previewItem.context}` : ""}</p>
              </div>
              <div className="flex items-center gap-1">
                <button type="button" className={cn(buttonVariants({ variant: "ghost", size: "sm" }))} onClick={() => setZoom((current) => Math.max(0.75, Number((current - 0.1).toFixed(2))))}>
                  <Minus className="h-4 w-4" />
                </button>
                <button type="button" className={cn(buttonVariants({ variant: "ghost", size: "sm" }))} onClick={() => setZoom((current) => Math.min(1.6, Number((current + 0.1).toFixed(2))))}>
                  <Plus className="h-4 w-4" />
                </button>
                <button type="button" className={cn(buttonVariants({ variant: "ghost", size: "sm" }))} onClick={() => setPreviewIndex((current) => (current === null ? current : (current - 1 + items.length) % items.length))}>
                  <ChevronLeft className="h-4 w-4" />
                </button>
                <button type="button" className={cn(buttonVariants({ variant: "ghost", size: "sm" }))} onClick={() => setPreviewIndex((current) => (current === null ? current : (current + 1) % items.length))}>
                  <ChevronRight className="h-4 w-4" />
                </button>
                <button type="button" className={cn(buttonVariants({ variant: "ghost", size: "sm" }))} onClick={() => setPreviewIndex(null)}>
                  <X className="h-4 w-4" />
                </button>
              </div>
            </div>

            <div className="grid gap-4 p-4 lg:grid-cols-[minmax(0,1fr)_220px]">
              <div className="flex min-h-[52vh] items-center justify-center overflow-hidden rounded-lg bg-slate-100 p-3">
                <img
                  src={previewItem.url}
                  alt={previewItem.label}
                  loading="eager"
                  decoding="async"
                  style={{ transform: `scale(${zoom})`, transformOrigin: "center center" }}
                  className="max-h-[78vh] w-auto rounded-lg border border-border object-contain transition-transform"
                />
              </div>

              <div className="max-h-[78vh] overflow-y-auto space-y-2 pr-1">
                <div className="rounded-lg border border-border bg-slate-50 p-3 text-xs text-slate-600">
                  <p className="text-eyebrow">Preview</p>
                  <p className="mt-2">{(previewIndex ?? 0) + 1} of {items.length}</p>
                  <p className="mt-1">Zoom {Math.round(zoom * 100)}%</p>
                </div>
                {items.map((shot, index) => (
                  <button
                    key={`${shot.url}-${index}`}
                    type="button"
                    className={cn(
                      "w-full overflow-hidden rounded-lg border text-left transition",
                      index === previewIndex ? "border-primary ring-2 ring-primary/20" : "border-border"
                    )}
                    onClick={() => setPreviewIndex(index)}
                  >
                    <div className="aspect-[4/3] overflow-hidden bg-slate-100">
                      <img src={shot.url} alt={shot.label} loading="lazy" decoding="async" className="h-full w-full object-cover" />
                    </div>
                    <div className="px-3 py-2 text-xs font-medium truncate text-slate-700 border-t border-border">{shot.label}</div>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
}
