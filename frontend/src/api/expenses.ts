import apiClient from "./client";
import type { ExpenseSavePayload, SavedExpense } from "../types";

export async function saveExpense(payload: ExpenseSavePayload) {
  const response = await apiClient.post<SavedExpense>("/expenses/", payload);
  return response.data;
}
