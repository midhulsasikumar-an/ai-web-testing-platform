"use client";

import React, { useEffect, useState } from 'react';
import { collaborationApi } from '@/services/collaboration-api';
import { ActivityEvent } from '@/types/collaboration';
import { ActivityTimeline } from '@/components/collaboration/activity-timeline';
import { Header } from '@/components/layout/header';

export default function ActivityPage() {
  const [events, setEvents] = useState<ActivityEvent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const data = await collaborationApi.getActivity();
        setEvents(data);
      } catch (err) {
        console.error("Failed to load activity", err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  return (
    <div className="flex-1 overflow-y-auto bg-background p-6">
      <div className="max-w-4xl mx-auto space-y-6">
        <Header 
          title="Team Activity" 
          description="A centralized feed of all events across your QA workspace." 
        />
        
        <div className="p-6 border rounded-xl bg-card">
          <h2 className="text-lg font-semibold mb-6">Recent Activity</h2>
          {loading ? (
            <div className="text-sm text-muted-foreground animate-pulse">Loading activity feed...</div>
          ) : (
            <ActivityTimeline events={events} />
          )}
        </div>
      </div>
    </div>
  );
}
