"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, SendHorizonal, Sparkles } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ErrorMessage } from "@/components/feedback/error-message";
import { ConversationSidebar } from "@/features/chat/components/conversation-sidebar";
import { CitationList, CitationPanel } from "@/features/citations/components/citation-list";
import { chatApi } from "@/services/endpoints/chat";
import { conversationsApi } from "@/services/endpoints/conversations";
import { useChatStore } from "@/stores/chat-store";
import type { Citation, LocalMessage } from "@/types/chat";
import type { ConversationState } from "@/types/conversations";

function ChatContent() {
  const queryClient = useQueryClient();
  const searchParams = useSearchParams();
  const activeId = useChatStore((state) => state.activeConversationId);
  const setActiveId = useChatStore((state) => state.setActiveConversationId);
  const setConversationState = useChatStore((state) => state.setConversationState);
  const updateConversationState = useChatStore((state) => state.updateConversationState);
  const setRetrievalTrace = useChatStore((state) => state.setRetrievalTrace);
  const draft = useChatStore((state) => state.draft);
  const setDraft = useChatStore((state) => state.setDraft);
  const [localMessages, setLocalMessages] = useState<LocalMessage[]>([]);
  const [isSending, setIsSending] = useState(false);

  useEffect(() => {
    setLocalMessages([]);
  }, [activeId]);

  useEffect(() => {
    const id = searchParams.get("conversation");
    if (id) setActiveId(id);
  }, [searchParams, setActiveId]);

  useEffect(() => {
    if (!activeId) {
      setConversationState(null);
    }
  }, [activeId, setConversationState]);

  const detail = useQuery({
    queryKey: ["conversation", activeId],
    queryFn: () => conversationsApi.detail(activeId as string),
    enabled: Boolean(activeId)
  });

  useEffect(() => {
    if (detail.data?.state) {
      setConversationState(detail.data.state);
    } else if (detail.isSuccess) {
      setConversationState(null);
    }
  }, [detail.data?.state, detail.isSuccess, setConversationState]);

  const messages = useMemo<LocalMessage[]>(() => {
    const persisted =
      detail.data?.messages.map((message) => ({
        id: message.id,
        role: message.role === "assistant" ? ("assistant" as const) : ("user" as const),
        content: message.content,
        created_at: message.created_at
      })) || [];
    return [...persisted, ...localMessages];
  }, [detail.data?.messages, localMessages]);

  const queryMutation = useMutation({
    mutationFn: chatApi.query,
    onSuccess: (response) => {
      setIsSending(false);
      setRetrievalTrace(response.retrieval_trace ?? response.retrieval_debug ?? null);
      if (response.retrieval_trace) {
        const nextState: Partial<ConversationState> = {};
        if (typeof response.retrieval_trace.active_document === "string") nextState.active_document_id = response.retrieval_trace.active_document;
        if (typeof response.retrieval_trace.active_chunk === "string") nextState.active_chunk_id = response.retrieval_trace.active_chunk;
        if (typeof response.retrieval_trace.source_document === "string") nextState.last_source_document = response.retrieval_trace.source_document;
        if (typeof response.retrieval_trace.retrieval_mode === "string") nextState.last_retrieval_mode = response.retrieval_trace.retrieval_mode;
        if (typeof response.retrieval_trace.answer_mode === "string") nextState.last_answer_mode = response.retrieval_trace.answer_mode;
        updateConversationState(nextState);
      }
      if (activeId) {
        setLocalMessages([]);
      } else {
        setLocalMessages((current) => [
          ...current.filter((message) => !message.pending),
          {
            id: crypto.randomUUID(),
            role: "assistant",
            content: response.answer,
            citations: response.citations,
            created_at: new Date().toISOString()
          }
        ]);
      }
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
      if (activeId) queryClient.invalidateQueries({ queryKey: ["conversation", activeId] });
    },
    onError: () => {
      setIsSending(false);
    }
  });

  async function handleCitationClick(citation: Citation) {
    updateConversationState({
      active_document_id: citation.document_id,
      active_chunk_id: citation.chunk_id,
      last_clicked_citation: citation,
      last_source_document: citation.filename
    });
    if (!activeId) return;
    try {
      await conversationsApi.patchState(activeId, {
        active_document_id: citation.document_id,
        active_chunk_id: citation.chunk_id,
        last_clicked_citation: citation,
        last_source_document: citation.filename
      });
      queryClient.invalidateQueries({ queryKey: ["conversation", activeId] });
    } catch {
      // Keep the UI responsive even if state persistence fails.
    }
  }

  async function send() {
    const text = draft.trim();
    if (!text || isSending || queryMutation.isPending) return;
    setIsSending(true);
    setDraft("");
    setLocalMessages((current) => [
      ...current,
      {
        id: crypto.randomUUID(),
        role: "user",
        content: text,
        created_at: new Date().toISOString()
      },
      {
        id: "pending",
        role: "assistant",
        content: "Thinking through the indexed sources...",
        created_at: new Date().toISOString(),
        pending: true
      }
    ]);
    queryMutation.mutate({ query: text, top_k: 5, conversation_id: activeId || undefined });
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[320px_minmax(0,1fr)]">
      <ConversationSidebar />
      <section className="flex h-[calc(100vh-8rem)] min-h-[620px] flex-col rounded-lg border bg-card">
        <div className="flex h-14 items-center justify-between border-b px-4">
          <div>
            <p className="text-sm font-semibold">Chat Workspace</p>
            <p className="text-xs text-muted-foreground">Answers include citations when retrieval finds supporting evidence.</p>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto px-4 py-5">
          <div className="mx-auto max-w-3xl space-y-5">
            {messages.length ? (
              messages.map((message) => (
                <div key={message.id} className={message.role === "user" ? "flex justify-end" : "flex justify-start"}>
                  <div className={message.role === "user" ? "max-w-[85%] rounded-lg bg-primary px-4 py-3 text-primary-foreground" : "max-w-[90%] rounded-lg border bg-background px-4 py-3"}>
                    <div className="flex items-center gap-2">
                      {message.pending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                      <p className="whitespace-pre-wrap text-sm leading-6">{message.content}</p>
                    </div>
                    {message.citations ? <CitationList citations={message.citations} onCitationClick={handleCitationClick} /> : null}
                  </div>
                </div>
              ))
            ) : (
              <div className="flex min-h-[420px] flex-col items-center justify-center text-center">
                <Sparkles className="mb-4 h-10 w-10 text-primary" />
                <h1 className="text-xl font-semibold tracking-normal">Ask a grounded question</h1>
                <p className="mt-2 max-w-md text-sm text-muted-foreground">Upload a PDF, then ask about facts, summaries, requirements, or decisions inside the document.</p>
              </div>
            )}
            {queryMutation.error ? <ErrorMessage error={queryMutation.error} /> : null}
          </div>
        </div>
        <div className="border-t p-4">
          <div className="mx-auto flex max-w-3xl gap-2">
            <Textarea
              className="min-h-12 flex-1"
              placeholder="Ask about your uploaded documents..."
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  send();
                }
              }}
            />
            <Button className="h-12 w-12 px-0" disabled={!draft.trim() || isSending || queryMutation.isPending} onClick={send} title="Send">
              {queryMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <SendHorizonal className="h-4 w-4" />}
            </Button>
          </div>
        </div>
      </section>
      <CitationPanel />
    </div>
  );
}

export default function ChatPage() {
  return (
    <Suspense fallback={<div className="text-sm text-muted-foreground">Loading chat...</div>}>
      <ChatContent />
    </Suspense>
  );
}
