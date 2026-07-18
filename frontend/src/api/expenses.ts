import apiClient from "./client";
import type { Category, ExpenseSavePayload, MonthlySummaryResponse, SavedExpense } from "../types";

export async function fetchCategories() {
  const response = await apiClient.get<Category[]>("/categories/");
  return response.data;
}

export async function saveExpense(payload: ExpenseSavePayload) {
  const response = await apiClient.post<SavedExpense>("/expenses/", payload);
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

export async function fetchMonthlySummary(year: number, month: number) {
  const response = await apiClient.get<MonthlySummaryResponse>(`/summary/monthly/`, {
    params: { year, month },
  });
  return response.data;
}
