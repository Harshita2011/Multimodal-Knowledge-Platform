export type Citation = {
  document_id: string;
  filename: string;
  page_number: number;
  chunk_id: string;
  snippet: string;
};

export type QueryRequest = {
  query: string;
  top_k?: number;
  document_filter?: string;
  conversation_id?: string;
};

export type QueryResponse = {
  answer: string;
  citations: Citation[];
  retrieval_trace?: Record<string, unknown> | null;
  retrieval_debug?: Record<string, unknown> | null;
};

export type LocalMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  created_at: string;
  pending?: boolean;
};
