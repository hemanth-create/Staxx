/**
 * GlassPanel - Reusable glassmorphic container.
 * Semi-transparent background with blur effect and subtle border.
 */

export function GlassPanel({
  children,
  className = "",
  innerClassName = "",
  noPadding = false,
}) {
  const baseClasses =
    "relative rounded-lg backdrop-blur-md bg-white/3 border border-white/6 overflow-hidden";

  const paddingClass = noPadding ? "" : "p-6";

  return (
    <div className={`${baseClasses} ${className}`}>
      <div className={`${paddingClass} ${innerClassName}`}>{children}</div>
    </div>
  );
}
