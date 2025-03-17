import type { Metadata } from "next";
import Navbar from "@/components/ui/navbar";
import { ToastProvider } from "@/components/ui/use-toast";
import { Toaster } from "sonner";
import { Particles } from "@/components/ui/particles";

import "./globals.css";

export const metadata: Metadata = {
  title: "Rapster",
  description: "Created by Vasu and Ansh",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
    return (
      <html lang="en">
        <body className="bg-white overflow-x-hidden">
          <ToastProvider>
            {/* Fixed Navbar */}
            <Navbar />
  
            {/* Particles Behind Everything */}
            <Particles
              className="fixed inset-0 -z-10"
              quantity={300}
              ease={50}
              staticity={50}
              size={0.75}
              color="#222222"
              refresh
            />
  
            {/* Main content offset for the navbar */}
            <main className="pt-[72px] px-6">
              {children}
            </main>
  
            <Toaster />
          </ToastProvider>
        </body>
      </html>
    );
  }
  