import { useEffect, useState } from "react";
import type { Dispatch, ReactNode, SetStateAction } from "react";
import { Navigate, Route, Routes, useNavigate } from "react-router-dom";

import { fetchCurrentUser, loginUser, logoutUser, registerUser } from "./api/auth";
import AuthPage from "./pages/AuthPage";
import ComingSoonPage from "./pages/ComingSoonPage";
import HomePage from "./pages/HomePage";
import ReceiptCompletePage from "./pages/ReceiptCompletePage";
import ReceiptUploadPage from "./pages/ReceiptUploadPage";
import ExpenseListPage from "./pages/ExpenseListPage";
import ExpenseDetailPage from "./pages/ExpenseDetailPage";
import MonthlySummaryPage from "./pages/MonthlySummaryPage";
import type { AuthMode, LoginForm, RegisterForm, User } from "./types";
import { readableError, readableErrorStatus } from "./utils/errors";
import styles from "./App.module.css";

const initialLogin: LoginForm = {
  username: "",
  password: "",
};

const initialRegister: RegisterForm = {
  username: "",
  email: "",
  password: "",
};

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [loginForm, setLoginForm] = useState<LoginForm>(initialLogin);
  const [registerForm, setRegisterForm] = useState<RegisterForm>(initialRegister);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    async function initializeAuth() {
      try {
        const currentUser = await fetchCurrentUser();
        setUser(currentUser);
      } catch (requestError) {
        const status = readableErrorStatus(requestError);
        if (status !== 403 && status !== 401) {
          setError(readableError(requestError));
        }
      } finally {
        setAuthChecked(true);
      }
    }

    initializeAuth();
  }, []);

  async function handleRegister() {
    setError("");
    setMessage("");
    setIsSubmitting(true);

    try {
      await registerUser(registerForm);
      setRegisterForm(initialRegister);
      setMessage("登録が完了しました。ログインしてください。");
      return true;
    } catch (requestError) {
      setError(readableError(requestError));
      return false;
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleLogin() {
    setError("");
    setMessage("");
    setIsSubmitting(true);

    try {
      const loggedInUser = await loginUser(loginForm);
      setUser(loggedInUser);
      setLoginForm(initialLogin);
      setMessage("ログインしました。");
      return true;
    } catch (requestError) {
      setError(readableError(requestError));
      return false;
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleLogout() {
    setError("");
    setMessage("");
    setIsSubmitting(true);

    try {
      await logoutUser();
      setUser(null);
      setMessage("ログアウトしました。");
      navigate("/login", { replace: true });
    } catch (requestError) {
      setError(readableError(requestError));
    } finally {
      setIsSubmitting(false);
    }
  }

  if (!authChecked) {
    return <main className={styles.loadingShell}>読み込み中...</main>;
  }

  return (
    <Routes>
      <Route path="/" element={<Navigate to={user ? "/home" : "/login"} replace />} />
      <Route
        path="/login"
        element={renderAuthRoute({
          mode: "login",
          user,
          loginForm,
          registerForm,
          message,
          error,
          isSubmitting,
          onLogin: handleLogin,
          onRegister: handleRegister,
          setLoginForm,
          setRegisterForm,
        })}
      />
      <Route
        path="/register"
        element={renderAuthRoute({
          mode: "register",
          user,
          loginForm,
          registerForm,
          message,
          error,
          isSubmitting,
          onLogin: handleLogin,
          onRegister: handleRegister,
          setLoginForm,
          setRegisterForm,
        })}
      />
      <Route
        path="/home"
        element={
          user ? (
            <HomePage
              user={user}
              message={message}
              error={error}
              isSubmitting={isSubmitting}
              onLogout={handleLogout}
            />
          ) : (
            <Navigate to="/login" replace />
          )
        }
      />
      <Route
        path="/receipts/new"
        element={
          <ProtectedRoute user={user}>
            <ReceiptUploadPage
              onLogout={handleLogout}
              isSubmitting={isSubmitting}
            />
          </ProtectedRoute>
        }
      />
      <Route
        path="/expenses"
        element={
          <ProtectedRoute user={user}>
            <ExpenseListPage onLogout={handleLogout} isSubmitting={isSubmitting} />
          </ProtectedRoute>
        }
      />
      <Route
        path="/summary"
        element={
          <ProtectedRoute user={user}>
            <MonthlySummaryPage onLogout={handleLogout} isSubmitting={isSubmitting} />
          </ProtectedRoute>
        }
      />
      <Route
        path="/expenses/:expenseId"
        element={
          <ProtectedRoute user={user}>
            <ExpenseDetailPage onLogout={handleLogout} isSubmitting={isSubmitting} />
          </ProtectedRoute>
        }
      />
      <Route
        path="/receipts/complete"
        element={
          <ProtectedRoute user={user}>
            <ReceiptCompletePage onLogout={handleLogout} isSubmitting={isSubmitting} />
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<Navigate to={user ? "/home" : "/login"} replace />} />
    </Routes>
  );
}

type AuthRouteProps = {
  mode: AuthMode;
  user: User | null;
  loginForm: LoginForm;
  registerForm: RegisterForm;
  message: string;
  error: string;
  isSubmitting: boolean;
  onLogin: () => Promise<boolean>;
  onRegister: () => Promise<boolean>;
  setLoginForm: Dispatch<SetStateAction<LoginForm>>;
  setRegisterForm: Dispatch<SetStateAction<RegisterForm>>;
};

function renderAuthRoute(props: AuthRouteProps) {
  if (props.user) {
    return <Navigate to="/home" replace />;
  }

  return <AuthPage {...props} />;
}

function ProtectedRoute({ user, children }: { user: User | null; children: ReactNode }) {
  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return children;
}
