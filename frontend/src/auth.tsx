/** Authentication context: token lifecycle, current user, and company. */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { api, setUnauthorizedHandler, tokenStore, type Company, type User } from "./api";

interface AuthState {
  user: User | null;
  company: Company | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (data: {
    email: string;
    password: string;
    full_name: string;
    company_name: string;
    industry?: string;
  }) => Promise<void>;
  logout: () => void;
  refreshCompany: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [company, setCompany] = useState<Company | null>(null);
  const [loading, setLoading] = useState(true);

  const clear = useCallback(() => {
    tokenStore.clear();
    setUser(null);
    setCompany(null);
  }, []);

  // A 401 from any request drops us back to the login screen.
  useEffect(() => {
    setUnauthorizedHandler(() => {
      setUser(null);
      setCompany(null);
    });
  }, []);

  // Restore the session on first load if a token is present.
  useEffect(() => {
    const token = tokenStore.get();
    if (!token) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const [me, co] = await Promise.all([api.me(), api.getCompany()]);
        if (!cancelled) {
          setUser(me);
          setCompany(co);
        }
      } catch {
        if (!cancelled) clear();
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [clear]);

  const adopt = useCallback(async (token: string, nextUser: User) => {
    tokenStore.set(token);
    setUser(nextUser);
    setCompany(await api.getCompany());
  }, []);

  const login = useCallback(
    async (email: string, password: string) => {
      const result = await api.login(email, password);
      await adopt(result.access_token, result.user);
    },
    [adopt],
  );

  const register = useCallback(
    async (data: {
      email: string;
      password: string;
      full_name: string;
      company_name: string;
      industry?: string;
    }) => {
      const result = await api.register(data);
      await adopt(result.access_token, result.user);
    },
    [adopt],
  );

  const refreshCompany = useCallback(async () => {
    setCompany(await api.getCompany());
  }, []);

  const value = useMemo<AuthState>(
    () => ({ user, company, loading, login, register, logout: clear, refreshCompany }),
    [user, company, loading, login, register, clear, refreshCompany],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside an AuthProvider");
  return context;
}

/** Role gate for admin-only UI (metric editing, approvals, settings). */
export function useCanAdminister(): boolean {
  const { user } = useAuth();
  return user?.role === "OWNER" || user?.role === "ADMIN";
}
