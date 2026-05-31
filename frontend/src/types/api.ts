export type ApiErrorBody = {
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
    correlation_id?: string;
  };
};

export class ApiError extends Error {
  code: string;
  status: number;
  correlationId?: string;
  details?: Record<string, unknown>;

  constructor(message: string, status: number, code = "request_failed", correlationId?: string, details?: Record<string, unknown>) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.correlationId = correlationId;
    this.details = details;
  }
}

export type HealthStatus = {
  status?: string;
  database?: string;
  vector_store?: string;
  llm?: string;
  [key: string]: unknown;
};
