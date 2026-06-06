"use client";

import React, { useState, useEffect } from "react";
import { useAuth } from "@/context/auth-context";
import { Zap, Eye, EyeOff, ArrowRight, Loader2 } from "lucide-react";

export default function LoginPage() {
  const { login, error, clearError, isAuthenticated } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [shake, setShake] = useState(false);
  const [showSignup, setShowSignup] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  // Clear error when switching forms
  useEffect(() => {
    clearError();
  }, [showSignup, clearError]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isSubmitting) return;
    setIsSubmitting(true);

    const success = await login(email, password);
    if (!success) {
      setShake(true);
      setTimeout(() => setShake(false), 600);
    }
    setIsSubmitting(false);
  };

  if (isAuthenticated) return null;

  return (
    <div className="auth-page">
      {/* Animated background */}
      <div className="auth-bg">
        <div className="auth-gradient-orb auth-orb-1" />
        <div className="auth-gradient-orb auth-orb-2" />
        <div className="auth-gradient-orb auth-orb-3" />
        <div className="auth-grid-overlay" />

        {/* Floating particles */}
        {Array.from({ length: 20 }).map((_, i) => (
          <div
            key={i}
            className="auth-particle"
            style={{
              left: `${Math.random() * 100}%`,
              top: `${Math.random() * 100}%`,
              animationDelay: `${Math.random() * 8}s`,
              animationDuration: `${6 + Math.random() * 8}s`,
              width: `${2 + Math.random() * 4}px`,
              height: `${2 + Math.random() * 4}px`,
            }}
          />
        ))}
      </div>

      {/* Main content */}
      <div className={`auth-container ${mounted ? "auth-mounted" : ""}`}>
        {/* Brand */}
        <div className="auth-brand" style={{ animationDelay: "0.1s" }}>
          <div className="auth-logo">
            <div className="auth-logo-icon">
              <Zap className="h-6 w-6" />
            </div>
            <div className="auth-logo-glow" />
          </div>
          <h1 className="auth-title">SignalTrack</h1>
          <p className="auth-subtitle">Precision QA System</p>
        </div>

        {/* Glass Card */}
        <div className={`auth-card ${!showSignup && shake ? "auth-shake" : ""}`}>
          {!showSignup ? (
            /* ─── LOGIN FORM ─── */
            <form onSubmit={handleLogin} className="auth-form">
              <div className="auth-form-header" style={{ animationDelay: "0.2s" }}>
                <h2 className="auth-card-title">Welcome back</h2>
                <p className="auth-card-desc">Sign in to your account to continue</p>
              </div>

              {error && (
                <div className="auth-error" style={{ animationDelay: "0.25s" }}>
                  <span>{error}</span>
                </div>
              )}

              <div className="auth-field" style={{ animationDelay: "0.3s" }}>
                <div className="auth-input-wrapper">
                  <input
                    id="login-email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="auth-input"
                    placeholder=" "
                    required
                    autoComplete="email"
                  />
                  <label htmlFor="login-email" className="auth-label">
                    Email address
                  </label>
                  <div className="auth-input-glow" />
                </div>
              </div>

              <div className="auth-field" style={{ animationDelay: "0.4s" }}>
                <div className="auth-input-wrapper">
                  <input
                    id="login-password"
                    type={showPassword ? "text" : "password"}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="auth-input"
                    placeholder=" "
                    required
                    autoComplete="current-password"
                  />
                  <label htmlFor="login-password" className="auth-label">
                    Password
                  </label>
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="auth-eye-btn"
                    tabIndex={-1}
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                  <div className="auth-input-glow" />
                </div>
              </div>

              <button
                type="submit"
                disabled={isSubmitting}
                className="auth-submit-btn"
                style={{ animationDelay: "0.5s" }}
              >
                <span className="auth-btn-shimmer" />
                {isSubmitting ? (
                  <Loader2 className="h-5 w-5 animate-spin" />
                ) : (
                  <>
                    <span>Sign In</span>
                    <ArrowRight className="h-4 w-4" />
                  </>
                )}
              </button>

              <div className="auth-switch" style={{ animationDelay: "0.6s" }}>
                <span>Don&apos;t have an account?</span>
                <button
                  type="button"
                  onClick={() => setShowSignup(true)}
                  className="auth-switch-link"
                >
                  Create one
                </button>
              </div>
            </form>
          ) : (
            /* ─── SIGNUP FORM ─── */
            <SignupForm onSwitchToLogin={() => setShowSignup(false)} />
          )}
        </div>

        {/* Footer */}
        <p className="auth-footer" style={{ animationDelay: "0.7s" }}>
          AI-Powered Testing Platform
        </p>
      </div>
    </div>
  );
}


/* ─── Signup Form Component ─── */

function SignupForm({ onSwitchToLogin }: { onSwitchToLogin: () => void }) {
  const { signup, error, clearError } = useAuth();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [shake, setShake] = useState(false);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    clearError();
  }, [clearError]);

  const getPasswordStrength = (pw: string) => {
    let score = 0;
    if (pw.length >= 6) score++;
    if (pw.length >= 10) score++;
    if (/[A-Z]/.test(pw)) score++;
    if (/[0-9]/.test(pw)) score++;
    if (/[^A-Za-z0-9]/.test(pw)) score++;
    return score;
  };

  const strengthLabels = ["", "Weak", "Fair", "Good", "Strong", "Excellent"];
  const strengthColors = ["", "#ef4444", "#f97316", "#eab308", "#22c55e", "#06b6d4"];
  const pwStrength = getPasswordStrength(password);

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isSubmitting) return;
    setIsSubmitting(true);

    const ok = await signup(name, email, password);
    if (!ok) {
      setShake(true);
      setTimeout(() => setShake(false), 600);
    } else {
      setSuccess(true);
    }
    setIsSubmitting(false);
  };

  if (success) {
    return (
      <div className="auth-success">
        <div className="auth-success-check">
          <svg viewBox="0 0 24 24" className="auth-check-svg">
            <path
              d="M5 13l4 4L19 7"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="auth-check-path"
            />
          </svg>
        </div>
        <h3 className="auth-success-title">Account Created!</h3>
        <p className="auth-success-desc">Redirecting to dashboard…</p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSignup} className={`auth-form ${shake ? "auth-shake" : ""}`}>
      <div className="auth-form-header" style={{ animationDelay: "0.2s" }}>
        <h2 className="auth-card-title">Create Account</h2>
        <p className="auth-card-desc">Start testing with AI-powered insights</p>
      </div>

      {error && (
        <div className="auth-error" style={{ animationDelay: "0.25s" }}>
          <span>{error}</span>
        </div>
      )}

      <div className="auth-field" style={{ animationDelay: "0.25s" }}>
        <div className="auth-input-wrapper">
          <input
            id="signup-name"
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="auth-input"
            placeholder=" "
            required
            autoComplete="name"
          />
          <label htmlFor="signup-name" className="auth-label">
            Full name
          </label>
          <div className="auth-input-glow" />
        </div>
      </div>

      <div className="auth-field" style={{ animationDelay: "0.35s" }}>
        <div className="auth-input-wrapper">
          <input
            id="signup-email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="auth-input"
            placeholder=" "
            required
            autoComplete="email"
          />
          <label htmlFor="signup-email" className="auth-label">
            Email address
          </label>
          <div className="auth-input-glow" />
        </div>
      </div>

      <div className="auth-field" style={{ animationDelay: "0.45s" }}>
        <div className="auth-input-wrapper">
          <input
            id="signup-password"
            type={showPassword ? "text" : "password"}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="auth-input"
            placeholder=" "
            required
            minLength={6}
            autoComplete="new-password"
          />
          <label htmlFor="signup-password" className="auth-label">
            Password
          </label>
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="auth-eye-btn"
            tabIndex={-1}
          >
            {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </button>
          <div className="auth-input-glow" />
        </div>

        {/* Password strength */}
        {password.length > 0 && (
          <div className="auth-pw-strength">
            <div className="auth-pw-bar-track">
              <div
                className="auth-pw-bar-fill"
                style={{
                  width: `${(pwStrength / 5) * 100}%`,
                  backgroundColor: strengthColors[pwStrength],
                }}
              />
            </div>
            <span
              className="auth-pw-label"
              style={{ color: strengthColors[pwStrength] }}
            >
              {strengthLabels[pwStrength]}
            </span>
          </div>
        )}
      </div>

      <button
        type="submit"
        disabled={isSubmitting}
        className="auth-submit-btn"
        style={{ animationDelay: "0.55s" }}
      >
        <span className="auth-btn-shimmer" />
        {isSubmitting ? (
          <Loader2 className="h-5 w-5 animate-spin" />
        ) : (
          <>
            <span>Create Account</span>
            <ArrowRight className="h-4 w-4" />
          </>
        )}
      </button>

      <div className="auth-switch" style={{ animationDelay: "0.65s" }}>
        <span>Already have an account?</span>
        <button
          type="button"
          onClick={onSwitchToLogin}
          className="auth-switch-link"
        >
          Sign in
        </button>
      </div>
    </form>
  );
}
