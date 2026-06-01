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
};
