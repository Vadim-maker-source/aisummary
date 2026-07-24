import * as React from "react";
import { cn } from "@/lib/utils";

export function Table({
  className,
  ...props
}: React.ComponentProps<"table">) {
  return (
    <div data-slot="table-container" className="shad-table-container">
      <table
        data-slot="table"
        className={cn("shad-table", className)}
        {...props}
      />
    </div>
  );
}

export function TableHeader(props: React.ComponentProps<"thead">) {
  return <thead data-slot="table-header" {...props} />;
}

export function TableBody(props: React.ComponentProps<"tbody">) {
  return <tbody data-slot="table-body" {...props} />;
}

export function TableRow({
  className,
  ...props
}: React.ComponentProps<"tr">) {
  return (
    <tr data-slot="table-row" className={cn("shad-table-row", className)} {...props} />
  );
}

export function TableHead({
  className,
  ...props
}: React.ComponentProps<"th">) {
  return (
    <th data-slot="table-head" className={cn("shad-table-head", className)} {...props} />
  );
}

export function TableCell({
  className,
  ...props
}: React.ComponentProps<"td">) {
  return (
    <td data-slot="table-cell" className={cn("shad-table-cell", className)} {...props} />
  );
}
