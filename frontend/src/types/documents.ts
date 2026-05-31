export type UploadResponse = {
  document_id: string;
  filename: string;
  pages_processed: number;
  chunks_created: number;
  ingestion_timestamp: string;
  duration_ms: number;
};

export type DocumentSummary = {
  id: string;
  filename: string;
  status: string;
  page_count: number;
  chunk_count: number;
  created_at?: string | null;
  updated_at?: string | null;
};
