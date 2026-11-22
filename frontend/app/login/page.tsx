
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { supabase } from "@/lib/supabase";

type Mode = "signin" | "signup";
type LoginRole = "citizen" | "admin";

export default function LoginPage() {
  const router = useRouter();

  const [mode, setMode] = useState<Mode>("signin");
  const [loginRole, setLoginRole] = useState<LoginRole>("citizen");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  function friendlyError(
    msg: string,
    context: "signin" | "signup" = "signin"
  ): string {
    if (!msg) return "Something went wrong. Please try again.";

    const m = msg.toLowerCase();

    if (m.includes("email not confirmed")) {
      return "Please confirm your email address before signing in. Check your inbox for the confirmation link.";
    }

    if (m.includes("invalid login") || m.includes("invalid credentials")) {
      return "Incorrect email or password.";
    }

    if (
      m.includes("user already registered") ||
      m.includes("already exists")
    ) {
      return "An account with this email already exists. Please sign in instead.";
    }

    if (
      m.includes("password should be at least") ||
      m.includes("should be at least")
    ) {
      return msg;
    }

    if (m.includes("too many requests") || m.includes("rate limit")) {
      return "Too many attempts. Please wait a moment and try again.";
    }

    if (m.includes("network") || m.includes("fetch")) {
      return "Network error. Check your connection and try again.";
    }

    if (m.includes("signup") && m.includes("disabled")) {
      return "New signups are currently disabled on this project.";
    }

    return msg;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setMessage(null);
    setLoading(true);

    try {
      if (mode === "signin") {
        const { data, error: signInError } =
          await supabase.auth.signInWithPassword({
            email,
            password,
          });

        if (signInError) {
          setError(friendlyError(signInError.message, "signin"));
          return;
        }

        const user = data.user;
        const isAdmin = user?.app_metadata?.role === "admin";

        if (loginRole === "admin" && !isAdmin) {
          await supabase.auth.signOut();

          setError(
            "This account does not have administrator access. Please use Citizen Login or contact the administrator."
          );
          return;
        }

        if (loginRole === "admin") {
          router.push("/admin");
        } else {
          router.push("/reports");
        }

        return;
      }

      const { data: signUpData, error: signUpError } =
        await supabase.auth.signUp({
          email,
          password,
        });

      if (signUpError) {
        setError(friendlyError(signUpError.message, "signup"));
        return;
      }

      const identities = signUpData?.user?.identities;

      if (identities && identities.length === 0) {
        setError(
          "An account with this email already exists. Please sign in instead."
        );
        return;
      }

      setMessage(
        "Account created! Check your email for a confirmation link before signing in."
      );
    } catch {
      setError("Something went wrong. Check your connection and try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center px-4 py-12 bg-[hsl(217,33%,98%)]">
      <div className="w-full max-w-sm">
        <div className="bg-white rounded-2xl border border-border shadow-sm p-8">
          <div className="text-center mb-7">
            <div className="w-12 h-12 rounded-xl bg-primary flex items-center justify-center mx-auto mb-4">
              <svg
                className="w-6 h-6 text-white"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={1.5}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M15 10.5a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z"
                />
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1 1 15 0Z"
                />
              </svg>
            </div>

            <h1 className="text-xl font-bold">
              {mode === "signin" ? "Welcome back" : "Create your account"}
            </h1>

            <p className="text-sm text-muted-foreground mt-1">
              {mode === "signin"
                ? "Sign in to submit and track civic issue reports."
                : "Join CivicAI and start reporting civic issues."}
            </p>
          </div>

          {mode === "signin" && (
            <div className="grid grid-cols-2 gap-3 mb-5">
              <button
                type="button"
                onClick={() => {
                  setLoginRole("citizen");
                  setError(null);
                  setMessage(null);
                }}
                aria-pressed={loginRole === "citizen"}
                className={`rounded-xl border p-4 text-left transition-colors ${
                  loginRole === "citizen"
                    ? "border-primary bg-primary/5 ring-1 ring-primary"
                    : "border-border hover:bg-muted"
                }`}
              >
                <span className="block font-semibold text-sm">
                  Citizen Login
                </span>
                <span className="block text-xs text-muted-foreground mt-1">
                  File and track complaints
                </span>
              </button>

              <button
                type="button"
                onClick={() => {
                  setLoginRole("admin");
                  setError(null);
                  setMessage(null);
                }}
                aria-pressed={loginRole === "admin"}
                className={`rounded-xl border p-4 text-left transition-colors ${
                  loginRole === "admin"
                    ? "border-primary bg-primary/5 ring-1 ring-primary"
                    : "border-border hover:bg-muted"
                }`}
              >
                <span className="block font-semibold text-sm">
                  Admin Login
                </span>
                <span className="block text-xs text-muted-foreground mt-1">
                  View and manage all reports
                </span>
              </button>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label
                className="block text-sm font-medium mb-1.5 text-foreground"
                htmlFor="email"
              >
                Email address
              </label>
              <input
                id="email"
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full border border-input rounded-lg px-3 py-2.5 text-sm bg-background focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent transition-shadow"
                placeholder="you@example.com"
              />
            </div>

            <div>
              <label
                className="block text-sm font-medium mb-1.5 text-foreground"
                htmlFor="password"
              >
                Password
              </label>
              <input
                id="password"
                type="password"
                required
                autoComplete={
                  mode === "signin" ? "current-password" : "new-password"
                }
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full border border-input rounded-lg px-3 py-2.5 text-sm bg-background focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent transition-shadow"
                placeholder={
                  mode === "signup" ? "Choose a password" : "Your password"
                }
              />

              {mode === "signup" && (
                <p className="text-xs text-muted-foreground mt-1.5">
                  Choose a password. Supabase enforces its own minimum — if
                  your password is rejected, try a longer one.
                </p>
              )}
            </div>

            {error && (
              <div
                role="alert"
                className="flex items-start gap-2.5 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700"
              >
                <svg
                  className="w-4 h-4 mt-0.5 shrink-0"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126Z"
                  />
                </svg>
                <span>{error}</span>
              </div>
            )}

            {message && (
              <div
                role="status"
                className="flex items-start gap-2.5 p-3 bg-green-50 border border-green-200 rounded-lg text-sm text-green-700"
              >
                <svg
                  className="w-4 h-4 mt-0.5 shrink-0"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0Z"
                  />
                </svg>
                <span>{message}</span>
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-primary text-primary-foreground font-semibold py-2.5 rounded-lg hover:opacity-90 transition-opacity disabled:opacity-60 text-sm"
            >
              {loading ? (
                <span className="inline-flex items-center gap-2">
                  <svg
                    className="w-4 h-4 animate-spin"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 0 1 8-8V0C5.373 0 0 5.373 0 12h4z"
                    />
                  </svg>
                  Please wait…
                </span>
              ) : mode === "signin" ? (
                loginRole === "admin" ? "Admin Sign In" : "Citizen Sign In"
              ) : (
                "Create Account"
              )}
            </button>
          </form>

          <div className="mt-6 pt-5 border-t border-border text-center text-sm text-muted-foreground">
            {mode === "signin" ? (
              <>
                Don&apos;t have an account?{" "}
                <button
                  type="button"
                  onClick={() => {
                    setMode("signup");
                    setError(null);
                    setMessage(null);
                  }}
                  className="text-primary hover:underline font-medium"
                >
                  Create one
                </button>
              </>
            ) : (
              <>
                Already have an account?{" "}
                <button
                  type="button"
                  onClick={() => {
                    setMode("signin");
                    setError(null);
                    setMessage(null);
                  }}
                  className="text-primary hover:underline font-medium"
                >
                  Sign in
                </button>
              </>
            )}
          </div>
        </div>

        <p className="text-center text-xs text-muted-foreground mt-5">
          <Link
            href="/"
            className="hover:text-foreground transition-colors"
          >
            ← Back to CivicAI
          </Link>
        </p>
      </div>
    </div>
  );
}
