import React from 'react';
import { formatDistanceToNow } from 'date-fns';
import { Comment } from '@/types/collaboration';
import { User, CheckCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface CommentCardProps {
  comment: Comment;
  onMarkDecision?: (commentId: string) => void;
}

export function CommentCard({ comment, onMarkDecision }: CommentCardProps) {
  return (
    <div className="flex gap-4 p-4 border rounded-md bg-card mb-2 shadow-sm">
      <div className="mt-1">
        <div className="bg-muted w-8 h-8 rounded-full flex items-center justify-center text-muted-foreground">
          <User size={16} />
        </div>
      </div>
      <div className="flex-1 space-y-1">
        <div className="flex items-center justify-between">
          <div className="text-sm font-semibold">{comment.author_id}</div>
          <div className="text-xs text-muted-foreground">
            {formatDistanceToNow(new Date(comment.created_at), { addSuffix: true })}
          </div>
        </div>
        <div className="text-sm text-card-foreground whitespace-pre-wrap">
          {comment.body}
        </div>
        {comment.is_decision && (
          <div className="mt-2 inline-flex items-center gap-1 text-xs text-green-600 bg-green-500/10 px-2 py-1 rounded-md">
            <CheckCircle size={14} /> Marked as Decision
          </div>
        )}
        {!comment.is_decision && onMarkDecision && (
          <div className="flex justify-end">
            <Button variant="ghost" size="sm" className="text-xs h-6" onClick={() => onMarkDecision(comment.comment_id)}>
              Mark as Decision
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
