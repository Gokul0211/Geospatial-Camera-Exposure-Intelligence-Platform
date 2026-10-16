import * as React from "react";
import { Slot } from "radix-ui";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

/** Pill controls (radius lock, spec 5.3). Primary label is ink-0 on amber (9.5:1), never white. */
export const buttonVariants = cva(
  "inline-flex shrink-0 select-none items-center justify-center gap-2 whitespace-nowrap rounded-full font-medium transition-[background-color,color,transform,filter,border-color] duration-[160ms] ease-(--ease-out) active:scale-[0.98] disabled:pointer-events-none disabled:opacity-45 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        primary: "bg-signal text-ink-0 hover:brightness-110",
        secondary: "border border-line-strong bg-ink-2 text-bone hover:bg-ink-3",
        ghost: "bg-transparent text-bone-2 hover:bg-ink-2 hover:text-bone",
        link: "rounded-none px-0 text-bone underline decoration-line-strong underline-offset-[6px] hover:decoration-signal active:scale-100",
      },
      size: {
        sm: "h-9 px-4 text-sm",
        md: "h-11 px-6 text-[0.9375rem]",
        lg: "h-12 px-7 text-base",
      },
    },
    defaultVariants: { variant: "primary", size: "md" },
  },
);

export interface ButtonProps extends React.ComponentProps<"button">, VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

export function Button({ className, variant, size, asChild = false, type, ...props }: ButtonProps) {
  const Comp = asChild ? Slot.Root : "button";
  return (
    <Comp
      data-slot="button"
      type={asChild ? undefined : (type ?? "button")}
      className={cn(buttonVariants({ variant, size }), variant === "link" && "h-auto", className)}
      {...props}
    />
  );
}
