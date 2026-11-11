import { BACKEND_URL } from "../config/constants";

function extractErrorMessage(errorBody, fallbackMessage) {
  const validationError = errorBody?.detail?.[0];
  if (validationError?.msg) {
    const fieldName = validationError.loc?.[validationError.loc.length - 1];
    if (typeof fieldName === "string") {
      const normalizedFieldName = fieldName.replaceAll("_", " ");
      const label =
        normalizedFieldName.charAt(0).toUpperCase() +
        normalizedFieldName.slice(1);
      const normalizedMessage = validationError.msg.replace(/^String /, "");
      return `${label}: ${normalizedMessage}`;
    }
    return validationError.msg;
  }

  return errorBody?.error?.message || errorBody?.detail || fallbackMessage;
}

export async function fetchJson(path, { token = "", ...options } = {}) {
  const headers = {
    ...(options.body ? { "Content-Type": "application/json" } : {}),
    ...(options.headers || {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
  const response = await fetch(`${BACKEND_URL}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorMessage = "Request failed";
    try {
      const errorBody = await response.json();
      errorMessage = extractErrorMessage(errorBody, errorMessage);
    } catch {
      // keep default message when response body is not JSON
    }
    throw new Error(errorMessage);
  }

  if (response.status === 204) {
    return null;
  }
  return response.json();
}
