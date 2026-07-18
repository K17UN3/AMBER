import apiClient from "./client";
import type { OCRJob } from "../types";

export type OCRAvailability = {
  enabled: boolean;
  detail: string;
};

export async function getReceiptOcrAvailability() {
  const response = await apiClient.get<OCRAvailability>("/receipts/ocr-availability/");
  return response.data;
}

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
