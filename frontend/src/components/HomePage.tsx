"use client";

import AudioLibrary from "@/components/AudioLibrary";

export default function HomePage() {
  return (
    <main className="min-h-screen bg-black text-white flex flex-col items-center p-6">
      <h1 className="text-2xl font-bold mb-6">🎵 My Audio Library</h1>
      <AudioLibrary />
    </main>
  );
}
