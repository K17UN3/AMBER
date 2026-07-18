import axios from "axios";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim() || "http://localhost:8000/api";

const apiClient = axios.create({
  baseURL: apiBaseUrl,
  withCredentials: true,
  xsrfCookieName: "csrftoken",
  xsrfHeaderName: "X-CSRFToken",
  headers: {
    "Content-Type": "application/json",
  },
});

let csrfToken: string | null = null;
let csrfTokenRequest: Promise<string> | null = null;
const unsafeMethods = new Set(["delete", "patch", "post", "put"]);

function getCookie(name: string) {
  return document.cookie
    .split("; ")
    .find((row) => row.startsWith(`${name}=`))
    ?.split("=")[1];
}

async function fetchCsrfToken() {
  if (csrfToken) {
    return csrfToken;
  }

  if (!csrfTokenRequest) {
    csrfTokenRequest = apiClient
      .get<{ csrfToken: string }>("/auth/csrf/")
      .then((response) => {
        csrfToken = response.data.csrfToken;
        return csrfToken;
      })
      .finally(() => {
        csrfTokenRequest = null;
      });
  }

  return csrfTokenRequest;
}

apiClient.interceptors.request.use(async (config) => {
  const method = config.method?.toLowerCase();
  if (!method || !unsafeMethods.has(method)) {
    return config;
  }

  const cookieToken = getCookie("csrftoken");
  const token = cookieToken ? decodeURIComponent(cookieToken) : await fetchCsrfToken();
  config.headers.set("X-CSRFToken", token);
  return config;
});

export default apiClient;
