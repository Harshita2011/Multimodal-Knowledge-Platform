"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, FileUp, Loader2, UploadCloud } from "lucide-react";
import { useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ErrorMessage } from "@/components/feedback/error-message";
import { documentsApi } from "@/services/endpoints/documents";
import type { UploadResponse } from "@/types/documents";

const MAX_SIZE_MB = 25;

export default function UploadPage() {
  const queryClient = useQueryClient();
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [clientError, setClientError] = useState<string | null>(null);
  const [result, setResult] = useState<UploadResponse | null>(null);

  const uploadMutation = useMutation({
    mutationFn: (selected: File) => documentsApi.upload(selected),
    onSuccess: (data) => {
      setResult(data);
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    }
  });

  function validate(selected: File) {
    if (selected.type !== "application/pdf" && !selected.name.toLowerCase().endsWith(".pdf")) {
      return "Only PDF files are supported.";
    }
    if (selected.size > MAX_SIZE_MB * 1024 * 1024) {
      return `File must be ${MAX_SIZE_MB} MB or smaller.`;
    }
    return null;
  }

  function chooseFile(selected?: File) {
    if (!selected) return;
    const message = validate(selected);
    setClientError(message);
    setResult(null);
    setFile(message ? null : selected);
  }

  function upload() {
    if (!file) return;
    uploadMutation.mutate(file);
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-normal">Upload Center</h1>
        <p className="mt-1 text-sm text-muted-foreground">Add PDFs to the retrieval index and make them available for cited answers.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>PDF ingestion</CardTitle>
          <CardDescription>Documents are parsed, chunked, embedded, and stored for semantic retrieval.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          <div
            className="flex min-h-72 cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed bg-muted/40 p-8 text-center transition-colors hover:bg-muted"
            onClick={() => inputRef.current?.click()}
            onDragOver={(event) => event.preventDefault()}
            onDrop={(event) => {
              event.preventDefault();
              chooseFile(event.dataTransfer.files[0]);
            }}
          >
            <input ref={inputRef} className="hidden" type="file" accept="application/pdf,.pdf" onChange={(event) => chooseFile(event.target.files?.[0])} />
            <UploadCloud className="mb-4 h-10 w-10 text-primary" />
            <p className="text-base font-semibold">{file ? file.name : "Drop a PDF here"}</p>
            <p className="mt-2 max-w-md text-sm text-muted-foreground">Use a searchable PDF up to 25 MB. Scanned files without extractable text may fail during ingestion.</p>
            <Button className="mt-5" type="button" variant="secondary">
              <FileUp className="h-4 w-4" />
              Browse files
            </Button>
          </div>

          {clientError ? <ErrorMessage error={new Error(clientError)} /> : null}
          {uploadMutation.error ? <ErrorMessage error={uploadMutation.error} /> : null}

          <div className="flex justify-end">
            <Button disabled={!file || uploadMutation.isPending} onClick={upload}>
              {uploadMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <UploadCloud className="h-4 w-4" />}
              Upload and ingest
            </Button>
          </div>

          {result ? (
            <div className="rounded-lg border border-success/30 bg-success/10 p-4">
              <div className="flex items-center gap-2 text-success">
                <CheckCircle2 className="h-5 w-5" />
                <p className="font-medium">Ingestion complete</p>
              </div>
              <div className="mt-4 grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
                <div>
                  <p className="text-muted-foreground">Document ID</p>
                  <p className="truncate font-medium">{result.document_id}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Pages</p>
                  <p className="font-medium">{result.pages_processed}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Chunks</p>
                  <p className="font-medium">{result.chunks_created}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Duration</p>
                  <p className="font-medium">{result.duration_ms} ms</p>
                </div>
              </div>
            </div>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}
