export function AccountPanel({
  authMode,
  authEmail,
  authPassword,
  authUser,
  authErrorText,
  isAuthLoading,
  onAuthEmailChange,
  onAuthModeChange,
  onAuthPasswordChange,
  onAuthSubmit,
  onLogout,
}) {
  const submitLabel = authMode === "login" ? "Sign in" : "Create account";

  return (
    <aside className="hero-panel account-panel">
      <div className="account-header">
        <p className="section-kicker">Account</p>
        <h2>
          {authUser ? "Search history is active" : "Sign in to save searches"}
        </h2>
      </div>

      {authUser ? (
        <div className="account-summary">
          <div className="account-summary-card">
            <span>Signed in as</span>
            <strong>{authUser.email}</strong>
          </div>
          <p className="account-note">
            Every new search is saved automatically and can be reopened below.
          </p>
          <button className="secondary-button" type="button" onClick={onLogout}>
            Sign out
          </button>
        </div>
      ) : (
        <>
          <p className="account-note">
            Search still works without an account, but results will not be
            saved.
          </p>

          <div className="auth-toggle">
            <button
              className={
                authMode === "login"
                  ? "secondary-button secondary-button-active"
                  : "secondary-button"
              }
              type="button"
              onClick={() => onAuthModeChange("login")}
            >
              Sign in
            </button>
            <button
              className={
                authMode === "register"
                  ? "secondary-button secondary-button-active"
                  : "secondary-button"
              }
              type="button"
              onClick={() => onAuthModeChange("register")}
            >
              Create account
            </button>
          </div>

          <form className="account-form" onSubmit={onAuthSubmit}>
            <label className="field">
              <span>Email</span>
              <input
                type="email"
                value={authEmail}
                onChange={(event) => onAuthEmailChange(event.target.value)}
                placeholder="you@example.com"
              />
            </label>

            <label className="field">
              <span>Password</span>
              <input
                type="password"
                value={authPassword}
                onChange={(event) => onAuthPasswordChange(event.target.value)}
                placeholder="At least 8 characters"
              />
            </label>

            {authErrorText ? (
              <p className="inline-hint inline-hint-error">{authErrorText}</p>
            ) : null}

            <button
              className="cta-button account-submit"
              type="submit"
              disabled={isAuthLoading}
            >
              {isAuthLoading ? "Working..." : submitLabel}
            </button>
          </form>
        </>
      )}
    </aside>
  );
}
