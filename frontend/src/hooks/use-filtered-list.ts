"use client";

import { useState, useMemo } from "react";

// ── Types ──────────────────────────────────────────────────────────

interface UseFilteredListOptions<T> {
  /** Function to extract status from an item for filtering */
  getStatus?: (item: T) => string;
  /** Function to extract searchable text from an item */
  getSearchText?: (item: T) => string;
}

interface UseFilteredListReturn<T> {
  /** Currently filtered items */
  filtered: T[];
  /** Current status filter value */
  statusFilter: string;
  /** Set the status filter */
  setStatusFilter: (value: string) => void;
  /** Current search query */
  searchQuery: string;
  /** Set the search query */
  setSearchQuery: (value: string) => void;
}

// ── Hook ───────────────────────────────────────────────────────────

/**
 * Generic hook for filtering and searching a list of items.
 * Used by test-history and any future list pages.
 */
export function useFilteredList<T>(
  items: T[],
  options: UseFilteredListOptions<T> = {}
): UseFilteredListReturn<T> {
  const { getStatus, getSearchText } = options;

  const [statusFilter, setStatusFilter] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");

  const filtered = useMemo(() => {
    return items.filter((item) => {
      if (statusFilter !== "all" && getStatus) {
        if (getStatus(item) !== statusFilter) return false;
      }
      if (searchQuery && getSearchText) {
        if (!getSearchText(item).toLowerCase().includes(searchQuery.toLowerCase())) {
          return false;
        }
      }
      return true;
    });
  }, [items, statusFilter, searchQuery, getStatus, getSearchText]);

  return {
    filtered,
    statusFilter,
    setStatusFilter,
    searchQuery,
    setSearchQuery,
  };
}
