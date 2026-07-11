import apiClient from "./client";
import type { ExpenseSavePayload, SavedExpense } from "../types";

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
