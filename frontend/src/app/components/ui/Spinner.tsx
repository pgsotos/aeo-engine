interface SpinnerProps {
  /** Tailwind size classes. Defaults to the 1rem square used inside buttons. */
  className?: string;
}

/**
 * The inline loading indicator, shared by every async control.
 *
 * Purely decorative: the surrounding control carries the accessible label
 * ("Resolving categories…", "Running Evaluation…"), so this is hidden from
 * assistive technology rather than announced twice.
 */
export default function Spinner({ className = "h-4 w-4" }: SpinnerProps) {
  return (
    <svg
      className={`animate-spin ${className}`}
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
      focusable="false"
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
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
      />
    </svg>
  );
}
