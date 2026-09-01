"use client";

import { useEffect, useState, useCallback } from "react";
import { apiFetch } from "./api";
import { isAuthenticated, AUTH_CHANGED_EVENT } from "./auth";

type State = { loading: boolean; username: string | null };

export function useCurrentUser(): State {
  const [state, setState] = useState<State>({ loading: true, username: null });

  const fetchUser = useCallback(() => {
    if (!isAuthenticated()) {
      setState({ loading: false, username: null });
      return;
    }
    setState((s) => ({ ...s, loading: true }));
    apiFetch<{ username: string }>("/auth/me/")
      .then((data) => setState({ loading: false, username: data.username }))
      .catch(() => setState({ loading: false, username: null }));
  }, []);

  useEffect(() => {
    fetchUser();
    window.addEventListener(AUTH_CHANGED_EVENT, fetchUser);
    return () => window.removeEventListener(AUTH_CHANGED_EVENT, fetchUser);
  }, [fetchUser]);

  return state;
}