import apiClient from "./client";
import type { ClientOCRResult } from "../types";

export async function analyzeReceiptImage(image: File) {
  const formData = new FormData();
  formData.append("image", image);

  const response = await apiClient.post<ClientOCRResult>("/receipts/analyze/", formData);

  return response.data;
}
