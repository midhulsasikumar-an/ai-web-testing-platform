import { apiFetch } from "./api";
import type {
  Thread,
  Comment,
  ActivityEvent,
  Notification,
  Review,
  CollaborationObjectType,
  Decision,
} from "@/types/collaboration";

export const collaborationApi = {
  getOrCreateThread: (objectType: CollaborationObjectType, objectId: string, title?: string) => {
    return apiFetch(`/api/collaboration/threads/${objectType}/${objectId}${title ? `?title=${encodeURIComponent(title)}` : ""}`, {
      method: "POST",
    });
  },

  getThreadComments: (threadId: string) => {
    return apiFetch(`/api/collaboration/threads/${threadId}/comments`);
  },

  createComment: (threadId: string, body: string, parentCommentId?: string) => {
    return apiFetch(`/api/collaboration/threads/${threadId}/comments`, {
      method: "POST",
      body: JSON.stringify({ body, parent_comment_id: parentCommentId }),
    });
  },

  markCommentAsDecision: (commentId: string) => {
    return apiFetch(`/api/collaboration/comments/${commentId}/decision`, {
      method: "POST",
    });
  },

  getThreadDecisions: (threadId: string) => {
    return apiFetch(`/api/collaboration/threads/${threadId}/decisions`);
  },

  getActivity: () => {
    return apiFetch(`/api/collaboration/activity`);
  },

  getObjectActivity: (objectType: CollaborationObjectType, objectId: string) => {
    return apiFetch(`/api/collaboration/activity/${objectType}/${objectId}`);
  },

  getNotifications: () => {
    return apiFetch(`/api/collaboration/notifications`);
  },

  markNotificationRead: (notificationId: string) => {
    return apiFetch(`/api/collaboration/notifications/${notificationId}/read`, {
      method: "PATCH",
    });
  },

  markAllNotificationsRead: () => {
    return apiFetch(`/api/collaboration/notifications/read-all`, {
      method: "PATCH",
    });
  },

  requestReview: (objectType: CollaborationObjectType, objectId: string, workspaceId?: string, projectId?: string) => {
    return apiFetch(`/api/collaboration/reviews`, {
      method: "POST",
      body: JSON.stringify({ object_type: objectType, object_id: objectId, status: "pending", workspace_id: workspaceId, project_id: projectId }),
    });
  },

  getReviews: (objectType: CollaborationObjectType, objectId: string) => {
    return apiFetch(`/api/collaboration/reviews/${objectType}/${objectId}`);
  },

  updateReview: (reviewId: string, status: string, comment?: string) => {
    return apiFetch(`/api/collaboration/reviews/${reviewId}?status=${status}${comment ? `&comment=${encodeURIComponent(comment)}` : ""}`, {
      method: "PATCH",
    });
  },
};
