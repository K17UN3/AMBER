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
  if (!data) {
    return "通信に失敗しました。Djangoサーバーが起動しているか確認してください。";
  }

  if (typeof data.detail === "string") {
    return data.detail;
  }

  return Object.entries(data)
    .map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join(", ") : String(value)}`)
    .join("\n");
}

export function readableErrorStatus(error: unknown) {
  if (!isAxiosErrorResponse(error)) {
    return undefined;
  }

  return error.response?.status;
}

function isAxiosErrorResponse(error: unknown): error is AxiosError<ErrorResponse> {
  return axios.isAxiosError<ErrorResponse>(error);
}
