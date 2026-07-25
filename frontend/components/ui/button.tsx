import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva("shad-button", {
  variants: {
    variant: {
      default: "shad-button-default",
      secondary: "shad-button-secondary",
      outline: "shad-button-outline",
      ghost: "shad-button-ghost",
      destructive: "shad-button-destructive",
    },
    size: {
      default: "shad-button-md",
      sm: "shad-button-sm",
      icon: "shad-button-icon",
    },
  },
  defaultVariants: {
    variant: "default",
    size: "default",
  },
});

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

export function Button({
  className,
  variant,
  size,
  asChild = false,
  ...props
}: ButtonProps) {
  const Comp = asChild ? Slot : "button";

  return (
    <Comp
      data-slot="button"
      className={cn(buttonVariants({ variant, size }), className)}
      {...props}
    />
  );
}
