export type CollaborationObjectType =
  | "bug"
  | "test_run"
  | "test_result"
  | "ai_report"
  | "recommendation"
  | "screenshot"
  | "project";

export interface Thread {
  thread_id: string;
  workspace_id?: string;
  project_id?: string;
  object_type: CollaborationObjectType;
  object_id: string;
  title?: string;
  comment_count: number;
  last_activity_at?: string;
  created_by: string;
  created_at: string;
  updated_at?: string;
}

export interface Comment {
  comment_id: string;
  thread_id: string;
  author_id: string;
  author_name?: string;
  body: string;
  mentions: string[];
  parent_comment_id?: string | null;
  is_decision: boolean;
  created_at: string;
  updated_at?: string;
  deleted_at?: string | null;
}

export interface Decision {
  decision_id: string;
  thread_id: string;
  comment_id: string;
  object_type: CollaborationObjectType;
  object_id: string;
  decision_text: string;
  created_by: string;
  created_at: string;
}

export interface ActivityEvent {
  event_id: string;
  actor_id: string;
  actor_name?: string;
  event_type: string;
  object_type: CollaborationObjectType;
  object_id: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface Notification {
  notification_id: string;
  type: string;
  object_type: CollaborationObjectType;
  object_id: string;
  title: string;
  message: string;
  read: boolean;
  created_at: string;
}

export interface Review {
  review_id: string;
  object_type: CollaborationObjectType;
  object_id: string;
  reviewer_id: string;
  reviewer_name?: string;
  status: "pending" | "approved" | "changes_requested" | "dismissed";
  comment?: string;
  created_at: string;
  updated_at?: string;
}
