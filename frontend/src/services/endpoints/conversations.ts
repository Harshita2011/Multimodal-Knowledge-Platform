import { apiRequest } from "@/services/api-client";
import type { Conversation, ConversationDetail, ConversationState, ConversationStateUpdate } from "@/types/conversations";

export const conversationsApi = {
  list: () => apiRequest<Conversation[]>("/conversations", { method: "GET" }),
  create: (title = "Untitled") => apiRequest<Conversation>("/conversations", { method: "POST", body: { title } }),
  detail: (id: string) => apiRequest<ConversationDetail>(`/conversations/${id}`, { method: "GET" }),
  delete: (id: string) => apiRequest<{ ok: boolean }>(`/conversations/${id}`, { method: "DELETE" }),
  state: (id: string) => apiRequest<ConversationState>(`/conversations/${id}/state`, { method: "GET" }),
  patchState: (id: string, body: ConversationStateUpdate) => apiRequest<ConversationState>(`/conversations/${id}/state`, { method: "PATCH", body })
};
