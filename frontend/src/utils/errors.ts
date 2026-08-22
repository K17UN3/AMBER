import axios, { type AxiosError } from "axios";

function isMissingApiBaseUrlError(error: unknown) {
  return axios.isAxiosError(error) && error.message.includes("Unexpected token") && error.config?.baseURL === "http://localhost:8000/api";
}

type ErrorResponse = {
  detail?: string;
  [key: string]: unknown;
};

export function readableError(error: unknown) {
  if (!isAxiosErrorResponse(error)) {
    return "通信に失敗しました。Djangoサーバーが起動しているか確認してください。";
  }

  const data = error.response?.data;
  if (typeof data === "string") {
    const message = data.trim();
    if (message.startsWith("<!DOCTYPE html") || message.startsWith("<html")) {
      const status = error.response?.status;
      return status
        ? `サーバーでエラーが発生しました（${status}）。バックエンドのログを確認してください。`
        : "サーバーでエラーが発生しました。バックエンドのログを確認してください。";
    }
    return message || "通信に失敗しました。Djangoサーバーが起動しているか確認してください。";
  }

  if (!data || typeof data !== "object" || Array.isArray(data)) {
    return "通信に失敗しました。Djangoサーバーが起動しているか確認してください。";
  }

  const errorResponse = data as ErrorResponse;
  if (typeof errorResponse.detail === "string") {
    return errorResponse.detail;
  }

  return Object.entries(errorResponse)
    .map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join(", ") : String(value)}`)
    .join("\n");
}

export function readableErrorStatus(error: unknown) {
  if (!isAxiosErrorResponse(error)) {
    return undefined;
  }

  return error.response?.status;
}

function isAxiosErrorResponse(error: unknown): error is AxiosError<unknown> {
  return axios.isAxiosError(error);
}
