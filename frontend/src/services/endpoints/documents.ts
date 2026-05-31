import { apiRequest } from "@/services/api-client";
import type { DocumentSummary, UploadResponse } from "@/types/documents";

export const documentsApi = {
  upload: (file: File, documentId?: string) => {
    const form = new FormData();
    form.append("file", file);
    if (documentId) form.append("document_id", documentId);
    return apiRequest<UploadResponse>("/documents/upload", { method: "POST", body: form });
  },
  list: () => apiRequest<DocumentSummary[]>("/documents", { method: "GET" })
};
