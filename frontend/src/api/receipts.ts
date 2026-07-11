import apiClient from "./client";
import type { OCRJob } from "../types";

export async function startReceiptAnalysis(image: File) {
  const formData = new FormData();
  formData.append("image", image);

  const response = await apiClient.post<OCRJob>("/receipts/analyze/", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });

  return response.data;
}

export async function getReceiptAnalysisJob(jobId: string) {
  const response = await apiClient.get<OCRJob>(`/receipts/ocr-jobs/${jobId}/`);
  return response.data;
}
