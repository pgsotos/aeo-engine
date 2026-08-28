interface ErrorBannerProps {
  message: string | null;
}

/**
 * The single error surface for the page.
 *
 * `role="alert"` so a failure that appears after an action — a resolve that
 * timed out, a run that lost the backend — is announced rather than silently
 * painted above the fold the user is no longer looking at.
 */
export default function ErrorBanner({ message }: ErrorBannerProps) {
  if (!message) return null;

  return (
    <div
      role="alert"
      className="mb-6 rounded-lg border border-red-800/50 bg-red-900/20 px-4 py-3 text-sm text-red-300"
    >
      {message}
    </div>
  );
}
