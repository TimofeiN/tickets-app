import { useEffect, useState } from "react";
import { fetchJson } from "../api/client";
import { getStoredAuthToken, storeAuthToken } from "../api/authStorage";

export function useAuth({
  onSessionRestored,
  onSessionExpired,
  onSignedIn,
  onSignedOut,
}) {
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [token, setToken] = useState(getStoredAuthToken);
  const [user, setUser] = useState(null);
  const [errorText, setErrorText] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!token) return;

    async function bootstrapSession() {
      setIsLoading(true);
      try {
        const currentUser = await fetchJson("/auth/me", { token });
        setUser(currentUser);
        setErrorText("");
        await onSessionRestored(token);
      } catch {
        storeAuthToken("");
        setToken("");
        setUser(null);
        onSessionExpired();
      } finally {
        setIsLoading(false);
      }
    }

    void bootstrapSession();
  }, []);

  async function submit(event) {
    event.preventDefault();
    setIsLoading(true);
    setErrorText("");

    try {
      const data = await fetchJson(`/auth/${mode}`, {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      const nextToken = data.access_token || "";
      setToken(nextToken);
      setUser(data.user || null);
      setPassword("");
      storeAuthToken(nextToken);
      await onSignedIn(nextToken);
    } catch (error) {
      setErrorText(error.message || "Authentication failed");
    } finally {
      setIsLoading(false);
    }
  }

  async function logout() {
    try {
      if (token) {
        await fetchJson("/auth/logout", { method: "POST", token });
      }
    } catch {
      // clear local session even if logout request fails
    } finally {
      storeAuthToken("");
      setToken("");
      setUser(null);
      onSignedOut();
    }
  }

  return {
    mode,
    email,
    password,
    token,
    user,
    errorText,
    isLoading,
    setMode,
    setEmail,
    setPassword,
    submit,
    logout,
  };
}
