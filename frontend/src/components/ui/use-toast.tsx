"use client";

import { createContext, useContext, useState, ReactNode } from "react";
import { toast as sonnerToast } from "sonner"; // Using Sonner for toasts

type ToastContextType = {
  toast: {
    success: (message: string) => void;
    error: (message: string) => void;
  };
};

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export const ToastProvider = ({ children }: { children: ReactNode }) => {
  const [toasts, setToasts] = useState([]);

  return (
    <ToastContext.Provider
      value={{
        toast: {
          success: (message: string) => sonnerToast.success(message),
          error: (message: string) => sonnerToast.error(message),
        },
      }}
    >
      {children}
    </ToastContext.Provider>
  );
};

export const useToast = () => {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used within a ToastProvider");
  }
  return context;
};
