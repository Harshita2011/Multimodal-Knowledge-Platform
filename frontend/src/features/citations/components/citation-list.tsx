"use client";

import { FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useChatStore } from "@/stores/chat-store";
import type { Citation } from "@/types/chat";

export function CitationList({ citations }: { citations: Citation[] }) {
  const openCitation = useChatStore((state) => state.openCitation);
  if (!citations.length) return null;

  return (
    <div className="mt-4 space-y-2">
      <p className="text-xs font-semibold uppercase text-muted-foreground">Sources</p>
      <div className="grid gap-2 sm:grid-cols-2">
        {citations.map((citation) => (
          <button
            key={citation.chunk_id}
            className="rounded-md border bg-card p-3 text-left transition-colors hover:bg-muted focus:outline-none focus:ring-2 focus:ring-ring"
            onClick={() => openCitation(citation)}
          >
            <div className="flex items-center gap-2">
              <FileText className="h-4 w-4 text-primary" />
              <span className="min-w-0 flex-1 truncate text-sm font-medium">{citation.filename}</span>
              <Badge>p. {citation.page_number}</Badge>
            </div>
            <p className="mt-2 line-clamp-3 text-sm text-muted-foreground">{citation.snippet}</p>
          </button>
        ))}
      </div>
    </div>
  );
}

export function CitationPanel() {
  const citation = useChatStore((state) => state.selectedCitation);
  const open = useChatStore((state) => state.citationPanelOpen);
  const close = useChatStore((state) => state.closeCitation);

  if (!open || !citation) return null;

  return (
    <div className="fixed inset-y-0 right-0 z-40 w-full max-w-md border-l bg-card shadow-soft">
      <div className="flex h-16 items-center justify-between border-b px-5">
        <div>
          <p className="text-sm font-semibold">Citation detail</p>
          <p className="text-xs text-muted-foreground">Evidence used in the answer</p>
        </div>
        <Button variant="ghost" onClick={close}>
          Close
        </Button>
      </div>
      <div className="space-y-5 p-5">
        <div>
          <p className="text-xs font-medium uppercase text-muted-foreground">File</p>
          <p className="mt-1 text-sm font-medium">{citation.filename}</p>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-md border p-3">
            <p className="text-xs text-muted-foreground">Page</p>
            <p className="text-lg font-semibold">{citation.page_number}</p>
          </div>
          <div className="rounded-md border p-3">
            <p className="text-xs text-muted-foreground">Chunk</p>
            <p className="truncate text-sm font-medium">{citation.chunk_id}</p>
          </div>
        </div>
        <div>
          <p className="text-xs font-medium uppercase text-muted-foreground">Snippet</p>
          <p className="mt-2 rounded-md bg-muted p-4 text-sm leading-6">{citation.snippet}</p>
        </div>
      </div>
    </div>
  );
}
