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
      <body className="relative h-screen w-screen bg-white">
          <ToastProvider>
            {/* ✅ Navbar Fixed at Top */}
            <Navbar />

            {/* ✅ Particle Background */}
            <Particles className="absolute inset-0 -z-10 opacity-40" quantity={1000} ease={50} color="#222222" refresh />

            {/* ✅ Main Content with Padding for Navbar & Scrolling Support */}
            <div className="relative flex flex-col h-screen w-full pt-[72px] overflow-hidden">
              <main className="flex-1 w-full h-full p-6">
                {children}
              </main>
            </div>

            <Toaster />
          </ToastProvider>
      </body>
    </html>
  );
}
