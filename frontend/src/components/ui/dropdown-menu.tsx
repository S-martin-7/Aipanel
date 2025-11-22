"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { ChevronRight } from "lucide-react";

interface DropdownContextValue {
  open: boolean;
  setOpen: (open: boolean) => void;
}

const DropdownContext = React.createContext<DropdownContextValue | undefined>(undefined);

function useDropdown() {
  const context = React.useContext(DropdownContext);
  if (!context) {
    throw new Error("useDropdown must be used within a DropdownMenu");
  }
  return context;
}

interface DropdownMenuProps {
  children: React.ReactNode;
}

function DropdownMenu({ children }: DropdownMenuProps) {
  const [open, setOpen] = React.useState(false);

  return (
    <DropdownContext.Provider value={{ open, setOpen }}>
      <div className="relative inline-block">{children}</div>
    </DropdownContext.Provider>
  );
}

interface DropdownMenuTriggerProps {
  children: React.ReactNode;
  asChild?: boolean;
}

function DropdownMenuTrigger({ children, asChild }: DropdownMenuTriggerProps) {
  const { open, setOpen } = useDropdown();

  const handleClick = () => setOpen(!open);

  if (asChild && React.isValidElement(children)) {
    return React.cloneElement(children as React.ReactElement<{ onClick?: () => void }>, {
      onClick: handleClick,
    });
  }

  return (
    <button type="button" onClick={handleClick}>
      {children}
    </button>
  );
}

interface DropdownMenuContentProps extends React.HTMLAttributes<HTMLDivElement> {
  align?: "start" | "center" | "end";
}

function DropdownMenuContent({
  children,
  className,
  align = "end",
  ...props
}: DropdownMenuContentProps) {
  const { open, setOpen } = useDropdown();
  const contentRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (contentRef.current && !contentRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };

    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };

    if (open) {
      document.addEventListener("mousedown", handleClickOutside);
      document.addEventListener("keydown", handleEscape);
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [open, setOpen]);

  if (!open) return null;

  const alignClasses = {
    start: "left-0",
    center: "left-1/2 -translate-x-1/2",
    end: "right-0",
  };

  return (
    <div
      ref={contentRef}
      className={cn(
        "absolute z-50 mt-2 min-w-[8rem] overflow-hidden rounded-md border bg-popover p-1 text-popover-foreground shadow-md",
        "animate-in fade-in-0 zoom-in-95",
        alignClasses[align],
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}

interface DropdownMenuItemProps extends React.HTMLAttributes<HTMLDivElement> {
  inset?: boolean;
  disabled?: boolean;
}

function DropdownMenuItem({
  className,
  inset,
  disabled,
  onClick,
  ...props
}: DropdownMenuItemProps) {
  const { setOpen } = useDropdown();

  const handleClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (disabled) return;
    onClick?.(e);
    setOpen(false);
  };

  return (
    <div
      role="menuitem"
      className={cn(
        "relative flex cursor-pointer select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none transition-colors hover:bg-accent hover:text-accent-foreground focus:bg-accent focus:text-accent-foreground",
        inset && "pl-8",
        disabled && "pointer-events-none opacity-50",
        className
      )}
      onClick={handleClick}
      {...props}
    />
  );
}

function DropdownMenuSeparator({ className }: { className?: string }) {
  return <div className={cn("-mx-1 my-1 h-px bg-muted", className)} />;
}

function DropdownMenuLabel({
  className,
  inset,
  ...props
}: React.HTMLAttributes<HTMLDivElement> & { inset?: boolean }) {
  return (
    <div
      className={cn(
        "px-2 py-1.5 text-sm font-semibold",
        inset && "pl-8",
        className
      )}
      {...props}
    />
  );
}

interface DropdownMenuSubProps {
  children: React.ReactNode;
}

function DropdownMenuSub({ children }: DropdownMenuSubProps) {
  const [subOpen, setSubOpen] = React.useState(false);

  return (
    <DropdownContext.Provider value={{ open: subOpen, setOpen: setSubOpen }}>
      <div className="relative">{children}</div>
    </DropdownContext.Provider>
  );
}

function DropdownMenuSubTrigger({
  className,
  children,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  const { setOpen } = useDropdown();

  return (
    <div
      className={cn(
        "flex cursor-pointer select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none hover:bg-accent",
        className
      )}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      {...props}
    >
      {children}
      <ChevronRight className="ml-auto h-4 w-4" />
    </div>
  );
}

function DropdownMenuSubContent({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  const { open } = useDropdown();

  if (!open) return null;

  return (
    <div
      className={cn(
        "absolute left-full top-0 z-50 min-w-[8rem] overflow-hidden rounded-md border bg-popover p-1 text-popover-foreground shadow-lg",
        className
      )}
      {...props}
    />
  );
}

export {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuLabel,
  DropdownMenuSub,
  DropdownMenuSubTrigger,
  DropdownMenuSubContent,
};
