export type Conversation = {
  id: string;
  user_id: string;
  title: string;
  message_count: number;
  last_message_at: string | null;
};

export type ConversationMessage = {
  id: string;
  role: "user" | "assistant" | string;
  content: string;
  created_at: string;
};

export type ConversationDetail = Conversation & {
  messages: ConversationMessage[];
  state?: ConversationState | null;
};

export type ConversationState = {
  active_document_id: string | null;
  active_chunk_id: string | null;
  last_clicked_citation: {
    document_id: string;
    filename: string;
    page_number: number;
    chunk_id: string;
    snippet: string;
  } | null;
  last_source_document: string | null;
  last_retrieval_mode: string | null;
  last_answer_mode: string | null;
  updated_at: string | null;
};

export type ConversationStateUpdate = Partial<ConversationState>;
