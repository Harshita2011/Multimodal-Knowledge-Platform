"use client";

import { create } from "zustand";
import type { Citation } from "@/types/chat";

type ChatState = {
  activeConversationId: string | null;
  draft: string;
  selectedCitation: Citation | null;
  citationPanelOpen: boolean;
  setActiveConversationId: (id: string | null) => void;
  setDraft: (draft: string) => void;
  openCitation: (citation: Citation) => void;
  closeCitation: () => void;
};

export const useChatStore = create<ChatState>((set) => ({
  activeConversationId: null,
  draft: "",
  selectedCitation: null,
  citationPanelOpen: false,
  setActiveConversationId: (activeConversationId) => set({ activeConversationId }),
  setDraft: (draft) => set({ draft }),
  openCitation: (selectedCitation) => set({ selectedCitation, citationPanelOpen: true }),
  closeCitation: () => set({ selectedCitation: null, citationPanelOpen: false })
}));
