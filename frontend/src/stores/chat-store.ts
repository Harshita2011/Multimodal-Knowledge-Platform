"use client";

import { create } from "zustand";
import type { Citation } from "@/types/chat";
import type { ConversationState } from "@/types/conversations";

type ChatState = {
  activeConversationId: string | null;
  draft: string;
  selectedCitation: Citation | null;
  citationPanelOpen: boolean;
  conversationState: Partial<ConversationState> | null;
  retrievalTrace: Record<string, unknown> | null;
  setActiveConversationId: (id: string | null) => void;
  setDraft: (draft: string) => void;
  openCitation: (citation: Citation) => void;
  closeCitation: () => void;
  setConversationState: (state: Partial<ConversationState> | null) => void;
  updateConversationState: (state: Partial<ConversationState>) => void;
  setRetrievalTrace: (trace: Record<string, unknown> | null) => void;
};

export const useChatStore = create<ChatState>((set) => ({
  activeConversationId: null,
  draft: "",
  selectedCitation: null,
  citationPanelOpen: false,
  conversationState: null,
  retrievalTrace: null,
  setActiveConversationId: (activeConversationId) => set({ activeConversationId }),
  setDraft: (draft) => set({ draft }),
  openCitation: (selectedCitation) => set({ selectedCitation, citationPanelOpen: true }),
  closeCitation: () => set({ selectedCitation: null, citationPanelOpen: false }),
  setConversationState: (conversationState) => set({ conversationState }),
  updateConversationState: (state) =>
    set((current) => ({ conversationState: { ...(current.conversationState ?? {}), ...state } })),
  setRetrievalTrace: (retrievalTrace) => set({ retrievalTrace })
}));
