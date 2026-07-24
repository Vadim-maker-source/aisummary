import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva("shad-badge", {
  variants: {
    variant: {
      default: "shad-badge-default",
      secondary: "shad-badge-secondary",
      outline: "shad-badge-outline",
      warning: "shad-badge-warning",
      destructive: "shad-badge-destructive",
    },
  },
  defaultVariants: {
    variant: "secondary",
  },
});

export function Badge({
  className,
  variant,
  ...props
}: React.ComponentProps<"span"> & VariantProps<typeof badgeVariants>) {
  return (
    <span
      data-slot="badge"
      className={cn(badgeVariants({ variant }), className)}
      {...props}
    />
  );
}
