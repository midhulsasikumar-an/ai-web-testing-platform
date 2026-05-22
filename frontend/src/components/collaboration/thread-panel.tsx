"use client";

import React, { useEffect, useState } from 'react';
import { collaborationApi } from '@/services/collaboration-api';
import { Thread, Comment, CollaborationObjectType } from '@/types/collaboration';
import { CommentCard } from './comment-card';
import { CommentBox } from './comment-box';
import { MessageSquare } from 'lucide-react';

interface ThreadPanelProps {
  objectType: CollaborationObjectType;
  objectId: string;
  title?: string;
}

export function ThreadPanel({ objectType, objectId, title }: ThreadPanelProps) {
  const [thread, setThread] = useState<Thread | null>(null);
  const [comments, setComments] = useState<Comment[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function initThread() {
      try {
        const t = await collaborationApi.getOrCreateThread(objectType, objectId, title);
        setThread(t);
        const c = await collaborationApi.getThreadComments(t.thread_id);
        setComments(c);
      } catch (error) {
        console.error("Failed to load thread", error);
      } finally {
        setLoading(false);
      }
    }
    initThread();
  }, [objectType, objectId, title]);

  const handlePostComment = async (body: string) => {
    if (!thread) return;
    const newComment = await collaborationApi.createComment(thread.thread_id, body);
    setComments([...comments, newComment]);
  };

  const handleMarkDecision = async (commentId: string) => {
    try {
      await collaborationApi.markCommentAsDecision(commentId);
      setComments(comments.map(c => c.comment_id === commentId ? { ...c, is_decision: true } : c));
    } catch (error) {
      console.error("Failed to mark decision", error);
    }
  };

  if (loading) {
    return <div className="p-4 text-center text-sm text-muted-foreground animate-pulse">Loading discussion...</div>;
  }

  return (
    <div className="flex flex-col border rounded-lg bg-card overflow-hidden">
      <div className="flex items-center gap-2 p-3 border-b bg-muted/30">
        <MessageSquare size={16} className="text-muted-foreground" />
        <h3 className="text-sm font-semibold">Discussion</h3>
        <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded-full">
          {comments.length} comments
        </span>
      </div>
      <div className="p-4 max-h-[500px] overflow-y-auto flex flex-col gap-2">
        {comments.length === 0 ? (
          <div className="text-center text-sm text-muted-foreground py-8">
            No comments yet. Start the discussion!
          </div>
        ) : (
          comments.map(comment => (
            <CommentCard 
              key={comment.comment_id} 
              comment={comment} 
              onMarkDecision={handleMarkDecision} 
            />
          ))
        )}
      </div>
      <div className="p-4 border-t bg-muted/10">
        <CommentBox onSubmit={handlePostComment} />
      </div>
    </div>
  );
}
