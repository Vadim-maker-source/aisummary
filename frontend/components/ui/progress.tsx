import * as React from "react";
import { cn } from "@/lib/utils";

export function Progress({
  value = 0,
  className,
  ...props
}: React.ComponentProps<"div"> & { value?: number }) {
  const safeValue = Math.min(100, Math.max(0, value));

  return (
    <div
      data-slot="progress"
      className={cn("shad-progress", className)}
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={safeValue}
      {...props}
    >
      <div
        data-slot="progress-indicator"
        className="shad-progress-indicator"
        style={{ width: `${safeValue}%` }}
      />
    </div>
  );
}
