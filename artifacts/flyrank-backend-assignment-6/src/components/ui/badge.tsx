import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center rounded-[2px] border-2 border-foreground px-2.5 py-0.5 text-xs font-bold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 font-mono uppercase tracking-wider",
  {
    variants: {
      variant: {
        default:
          "bg-primary text-primary-foreground shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]",
        secondary:
          "bg-secondary text-secondary-foreground shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]",
        destructive:
          "bg-destructive text-destructive-foreground shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]",
        outline: "text-foreground shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]",
        success: "bg-green-400 text-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]",
        warning: "bg-yellow-400 text-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  )
}

export { Badge, badgeVariants }