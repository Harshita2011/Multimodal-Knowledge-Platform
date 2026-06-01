import { apiRequest } from "@/services/api-client";
import type { QueryRequest, QueryResponse } from "@/types/chat";

export const chatApi = {
  query: (body: QueryRequest) => apiRequest<QueryResponse>("/chat/query", { method: "POST", body })
};
