"use client";

import { useQuery } from "@tanstack/react-query";
import { FileText, MessageSquareText, Plus, UploadCloud } from "lucide-react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/feedback/empty-state";
import { formatDateTime } from "@/lib/utils";
import { conversationsApi } from "@/services/endpoints/conversations";
import { documentsApi } from "@/services/endpoints/documents";
import { healthApi } from "@/services/endpoints/health";
import { useAuthStore } from "@/stores/auth-store";

export default function DashboardPage() {
  const user = useAuthStore((state) => state.user);
  const conversations = useQuery({ queryKey: ["conversations"], queryFn: conversationsApi.list });
  const documents = useQuery({ queryKey: ["documents"], queryFn: documentsApi.list, retry: false });
  const health = useQuery({ queryKey: ["health"], queryFn: healthApi.get, retry: false });

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <div className="flex flex-col justify-between gap-4 md:flex-row md:items-end">
        <div>
          <h1 className="text-2xl font-semibold tracking-normal">Dashboard</h1>
          <p className="mt-1 text-sm text-muted-foreground">Welcome{user?.name ? `, ${user.name}` : ""}. Your knowledge workspace is ready.</p>
        </div>
        <div className="flex gap-2">
          <Button asChild variant="secondary">
            <Link href="/upload">
              <UploadCloud className="h-4 w-4" />
              Upload
            </Link>
          </Button>
          <Button asChild>
            <Link href="/chat">
              <Plus className="h-4 w-4" />
              New chat
            </Link>
          </Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>Profile</CardTitle>
            <CardDescription>{user?.email}</CardDescription>
          </CardHeader>
          <CardContent>
            <Badge>{user?.provider ? `${user.provider} connected` : "Password account"}</Badge>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Backend health</CardTitle>
            <CardDescription>FastAPI service status</CardDescription>
          </CardHeader>
          <CardContent>
            <Badge className={health.isError ? "border-destructive/40 text-destructive" : "border-success/40 text-success"}>
              {health.isError ? "Unavailable" : String(health.data?.status || "Online")}
            </Badge>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Knowledge base</CardTitle>
            <CardDescription>Indexed PDFs</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-semibold">{documents.data?.length ?? 0}</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Recent conversations</CardTitle>
            <CardDescription>Continue from your latest questions</CardDescription>
          </CardHeader>
          <CardContent>
            {conversations.data?.length ? (
              <div className="space-y-2">
                {conversations.data.slice(0, 5).map((conversation) => (
                  <Link key={conversation.id} className="flex items-center gap-3 rounded-md border p-3 hover:bg-muted" href={`/chat?conversation=${conversation.id}`}>
                    <MessageSquareText className="h-4 w-4 text-primary" />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium">{conversation.title}</p>
                      <p className="text-xs text-muted-foreground">{formatDateTime(conversation.last_message_at)}</p>
                    </div>
                    <Badge>{conversation.message_count}</Badge>
                  </Link>
                ))}
              </div>
            ) : (
              <EmptyState icon={<MessageSquareText className="h-6 w-6" />} title="No conversations yet" description="Start a chat once your first document is ready." />
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Uploaded documents</CardTitle>
            <CardDescription>Documents available for retrieval</CardDescription>
          </CardHeader>
          <CardContent>
            {documents.isError ? (
              <EmptyState
                icon={<FileText className="h-6 w-6" />}
                title="Document list endpoint pending"
                description="Uploads work now. Add GET /api/v1/documents on the backend to show this list."
                action={
                  <Button asChild variant="secondary">
                    <Link href="/upload">Upload PDF</Link>
                  </Button>
                }
              />
            ) : documents.data?.length ? (
              <div className="space-y-2">
                {documents.data.map((doc) => (
                  <div key={doc.id} className="flex items-center gap-3 rounded-md border p-3">
                    <FileText className="h-4 w-4 text-primary" />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium">{doc.filename}</p>
                      <p className="text-xs text-muted-foreground">
                        {doc.page_count} pages, {doc.chunk_count} chunks
                      </p>
                    </div>
                    <Badge>{doc.status}</Badge>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState icon={<FileText className="h-6 w-6" />} title="No documents uploaded" description="Upload PDFs to make grounded chat useful." />
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
