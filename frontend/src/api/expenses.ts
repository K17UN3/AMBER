import apiClient from "./client";
import type { Category, ExpenseSavePayload, MonthlySummaryResponse, SavedExpense } from "../types";

export async function fetchCategories() {
  const response = await apiClient.get<Category[]>("/categories/");
  return response.data;
}

export async function classifyCategory(shopName: string, rawOcrText: string) {
  const response = await apiClient.post<Category>("/categories/classify/", {
    shop_name: shopName,
    raw_ocr_text: rawOcrText,
  });
  return response.data;
}

export async function saveExpense(payload: ExpenseSavePayload, image?: File | null) {
  const response = await apiClient.post<SavedExpense>(
    "/expenses/",
    image ? buildExpenseFormData(payload, image) : payload,
    image ? multipartConfig : undefined,
  );
  return response.data;
}

export async function fetchExpenses() {
  const response = await apiClient.get<SavedExpense[]>("/expenses/");
  return response.data;
}

export async function fetchExpenseDetail(id: number) {
  const response = await apiClient.get<SavedExpense>(`/expenses/${id}/`);
  return response.data;
}

export async function updateExpense(id: number, payload: ExpenseSavePayload, image?: File | null) {
  const response = await apiClient.put<SavedExpense>(
    `/expenses/${id}/`,
    image ? buildExpenseFormData(payload, image) : payload,
    image ? multipartConfig : undefined,
  );
  return response.data;
}

export async function deleteExpense(id: number) {
  await apiClient.delete(`/expenses/${id}/`);
}

export async function fetchMonthlySummary(year: number, month: number) {
  const response = await apiClient.get<MonthlySummaryResponse>(`/summary/monthly/`, {
    params: { year, month },
  });
  return response.data;
}

const multipartConfig = {
  headers: { "Content-Type": "multipart/form-data" },
};

function buildExpenseFormData(payload: ExpenseSavePayload, image: File) {
  const formData = new FormData();
  formData.append("shop_name", payload.shop_name);
  formData.append("purchased_at", payload.purchased_at);
  formData.append("total_amount", String(payload.total_amount));
  formData.append("category", payload.category);
  formData.append("raw_ocr_text", payload.raw_ocr_text);
  if (payload.ocr_result) {
    formData.append("ocr_result", JSON.stringify(payload.ocr_result));
  }
  formData.append("image", image);
  return formData;
}
