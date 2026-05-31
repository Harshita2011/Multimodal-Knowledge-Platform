"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { MessageSquarePlus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/feedback/empty-state";
import { cn, formatDateTime } from "@/lib/utils";
import { conversationsApi } from "@/services/endpoints/conversations";
import { useChatStore } from "@/stores/chat-store";

export function ConversationSidebar() {
  const queryClient = useQueryClient();
  const activeId = useChatStore((state) => state.activeConversationId);
  const setActiveId = useChatStore((state) => state.setActiveConversationId);
  const conversations = useQuery({ queryKey: ["conversations"], queryFn: conversationsApi.list });

  const createMutation = useMutation({
    mutationFn: () => conversationsApi.create("New conversation"),
    onSuccess: (conversation) => {
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
      setActiveId(conversation.id);
    }
  });

  const deleteMutation = useMutation({
    mutationFn: conversationsApi.delete,
    onSuccess: (_, id) => {
      if (activeId === id) setActiveId(null);
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
    }
  });

  return (
    <aside className="h-[calc(100vh-8rem)] rounded-lg border bg-card">
      <div className="flex h-14 items-center justify-between border-b px-3">
        <p className="text-sm font-semibold">Conversations</p>
        <Button size="icon" variant="ghost" title="New conversation" onClick={() => createMutation.mutate()}>
          <MessageSquarePlus className="h-4 w-4" />
        </Button>
      </div>
      <div className="h-[calc(100%-3.5rem)] overflow-y-auto p-2">
        {conversations.data?.length ? (
          <div className="space-y-1">
            {conversations.data.map((conversation) => (
              <div
                key={conversation.id}
                className={cn(
                  "group flex items-center gap-2 rounded-md p-2 transition-colors hover:bg-muted",
                  activeId === conversation.id && "bg-primary/10"
                )}
              >
                <button className="min-w-0 flex-1 text-left" onClick={() => setActiveId(conversation.id)}>
                  <p className="truncate text-sm font-medium">{conversation.title}</p>
                  <p className="truncate text-xs text-muted-foreground">{formatDateTime(conversation.last_message_at)}</p>
                </button>
                <Button className="h-8 w-8 opacity-0 group-hover:opacity-100" size="icon" variant="ghost" onClick={() => deleteMutation.mutate(conversation.id)}>
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState title="No chats" description="Create a conversation to preserve your Q&A history." />
        )}
      </div>
    </aside>
  );
}
