import { apiRequest } from "@/services/api-client";
import type { HealthStatus } from "@/types/api";

export const healthApi = {
  get: () => apiRequest<HealthStatus>("/health", { method: "GET", auth: false })
};
