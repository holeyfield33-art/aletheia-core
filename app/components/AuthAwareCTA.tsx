import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";

interface CTAProps {
  anonymousLabel?: string;
  anonymousHref?: string;
  authedLabel?: string;
  authedHref?: string;
  variant?: "primary" | "secondary";
  secondaryAnonymousLabel?: string;
  secondaryAnonymousHref?: string;
}

export default async function AuthAwareCTA({
  anonymousLabel = "Protect My Agent",
  anonymousHref = "/auth/register",
  authedLabel = "Open Dashboard",
  authedHref = "/dashboard",
  variant = "primary",
  secondaryAnonymousLabel,
  secondaryAnonymousHref,
}: CTAProps) {
  const session = await getServerSession(authOptions);
  const isAuthed = Boolean(session?.user?.id);
  const className = variant === "primary" ? "btn-primary" : "btn-secondary";

  if (isAuthed) {
    return (
      <a href={authedHref} className={className}>
        {authedLabel}
      </a>
    );
  }
  return (
    <>
      <a href={anonymousHref} className={className}>
        {anonymousLabel}
      </a>
      {secondaryAnonymousLabel && secondaryAnonymousHref && (
        <a href={secondaryAnonymousHref} className="btn-secondary">
          {secondaryAnonymousLabel}
        </a>
      )}
    </>
  );
}
