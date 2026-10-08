import { ArrowRight, Eye, EyeOff, LockKeyhole, Sparkles } from "lucide-react";
import { useState, type FormEvent } from "react";
import { supabase } from "../lib/supabase";

export function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleLogin = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const { error: signInError } = await supabase.auth.signInWithPassword({
        email,
        password,
      });
      if (signInError) setError(signInError.message);
    } catch (signInError) {
      setError(
        signInError instanceof Error
          ? signInError.message
          : "Unable to sign in. Please try again.",
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="login-screen">
      <section className="login-card" aria-label="Sign in to Canta Social Copilot">
        <div className="login-showcase">
          <div className="login-brand">
            <span className="login-brand-mark" aria-hidden="true">C</span>
            <span>Canta<span className="login-brand-light">Social Copilot</span></span>
          </div>

          <div className="login-showcase-copy">
            <span className="login-kicker"><Sparkles size={14} aria-hidden="true" /> YOUR IDEAS, IN MOTION</span>
            <h1>Make your next post your best one.</h1>
            <p>One calm, considered workspace for shaping ideas into social content you’re proud to publish.</p>
          </div>

          <div className="login-preview" aria-hidden="true">
            <div className="login-preview-topline">
              <span className="login-preview-dot" />
              <span>YOUR CONTENT WORKSPACE</span>
              <span className="login-preview-live">READY</span>
            </div>
            <div className="login-preview-post">
              <span className="login-preview-label">A GOOD IDEA STARTS HERE</span>
              <span className="login-preview-title">Turn what you know into something worth sharing.</span>
              <div className="login-preview-tags">
                <span>LinkedIn</span>
                <span>X</span>
                <span>Draft</span>
              </div>
            </div>
            <div className="login-preview-footer">
              <span className="login-preview-check">✓</span>
              <span>Thoughtful by design. Always yours to approve.</span>
            </div>
          </div>

          <p className="login-showcase-footnote">Plan with purpose. Publish with confidence.</p>
        </div>

        <div className="login-form-panel">
          <div className="login-form-heading">
            <div className="login-mobile-brand">
              <span className="login-brand-mark" aria-hidden="true">C</span>
              <strong>Canta</strong>
            </div>
            <span className="login-welcome">WELCOME BACK</span>
            <h2>Sign in to your workspace</h2>
            <p>Your next great post is a few steps away.</p>
          </div>

          {error && (
            <div className="login-error" role="alert">
              <span className="login-error-icon" aria-hidden="true">!</span>
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleLogin} className="login-form">
            <div className="login-field">
              <label htmlFor="login-email">Email address</label>
              <input
                id="login-email"
                type="email"
                autoComplete="email"
                placeholder="you@example.com"
                required
                value={email}
                onChange={(event) => setEmail(event.target.value)}
              />
            </div>

            <div className="login-field">
              <div className="login-password-label">
                <label htmlFor="login-password">Password</label>
                <span><LockKeyhole size={13} aria-hidden="true" /> SECURE SIGN IN</span>
              </div>
              <div className="login-password-input">
                <input
                  id="login-password"
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  placeholder="Enter your password"
                  required
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                />
                <button
                  type="button"
                  className="login-password-toggle"
                  onClick={() => setShowPassword((visible) => !visible)}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  aria-pressed={showPassword}
                >
                  {showPassword ? <EyeOff size={17} /> : <Eye size={17} />}
                </button>
              </div>
            </div>

            <button className="login-submit" type="submit" disabled={loading}>
              <span>{loading ? "Signing you in..." : "Sign in"}</span>
              {!loading && <ArrowRight size={17} aria-hidden="true" />}
              {loading && <span className="login-submit-spinner" aria-hidden="true" />}
            </button>
          </form>

          <div className="login-security-note">
            <LockKeyhole size={15} aria-hidden="true" />
            <span>Your account is protected with secure authentication.</span>
          </div>
          <p className="login-copyright">Canta Social Copilot <span>·</span> Create with intention.</p>
        </div>
      </section>
    </main>
  );
}
