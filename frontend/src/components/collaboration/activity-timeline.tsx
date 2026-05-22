import React from 'react';
import { formatDistanceToNow } from 'date-fns';
import { ActivityEvent } from '@/types/collaboration';
import { CircleDot } from 'lucide-react';

interface ActivityTimelineProps {
  events: ActivityEvent[];
}

export function ActivityTimeline({ events }: ActivityTimelineProps) {
  if (events.length === 0) {
    return <div className="text-sm text-muted-foreground italic py-4">No recent activity.</div>;
  }

  return (
    <div className="space-y-4">
      {events.map((event, i) => (
        <div key={event.event_id} className="flex gap-3">
          <div className="flex flex-col items-center">
            <div className="mt-1">
              <CircleDot size={14} className="text-muted-foreground" />
            </div>
            {i !== events.length - 1 && (
              <div className="w-px h-full bg-border my-1" />
            )}
          </div>
          <div className="flex-1 pb-4">
            <div className="text-sm">
              <span className="font-medium">{event.actor_id}</span>
              <span className="text-muted-foreground mx-1">
                {formatEventType(event.event_type)}
              </span>
              {event.metadata?.title && (
                <span className="font-medium">"{event.metadata.title as string}"</span>
              )}
            </div>
            <div className="text-xs text-muted-foreground mt-1">
              {formatDistanceToNow(new Date(event.created_at), { addSuffix: true })}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

function formatEventType(type: string) {
  const map: Record<string, string> = {
    "test_run.created": "started a test run",
    "test_run.completed": "completed a test run",
    "bug.created": "created a bug",
    "comment.created": "commented on",
    "comment.marked_as_decision": "marked a decision on",
    "review.requested": "requested a review",
  };
  return map[type] || type.replace(".", " ");
}
