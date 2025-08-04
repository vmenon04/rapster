"use client";

import AudioLibrary from "@/components/AudioLibrary";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { AuthModal } from "@/components/auth/AuthModal";
import { useState } from "react";
import { Music, Upload, Users } from "lucide-react";

export default function HomePage() {
  const { isAuthenticated, user } = useAuth();
  const [authModalOpen, setAuthModalOpen] = useState(false);

  return (
    <main className="min-h-screen bg-black text-white flex flex-col">
      {/* Hero Section */}
      <div className="flex flex-col items-center justify-center py-20 px-6">
        <div className="text-center max-w-4xl mx-auto">
          <h1 className="text-4xl md:text-6xl font-bold mb-6 bg-gradient-to-r from-blue-400 to-purple-600 bg-clip-text text-transparent">
            Welcome to Rapster
          </h1>
          <p className="text-xl md:text-2xl text-gray-300 mb-8">
            A crowdsourced music streaming platform where anyone can upload and share their music
          </p>
          
          {!isAuthenticated ? (
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Button
                size="lg"
                onClick={() => setAuthModalOpen(true)}
                className="bg-blue-600 hover:bg-blue-700"
              >
                <Music className="mr-2 h-5 w-5" />
                Get Started
              </Button>
              <Button
                size="lg"
                variant="outline"
                onClick={() => setAuthModalOpen(true)}
                className="border-gray-600 text-gray-300 hover:bg-gray-800"
              >
                <Upload className="mr-2 h-5 w-5" />
                Upload Music
              </Button>
            </div>
          ) : (
            <div className="text-center">
              <p className="text-lg text-gray-300 mb-4">
                Welcome back, <span className="text-blue-400 font-semibold">{user?.username}</span>!
              </p>
              <Button
                size="lg"
                onClick={() => window.location.href = '/upload'}
                className="bg-green-600 hover:bg-green-700"
              >
                <Upload className="mr-2 h-5 w-5" />
                Upload New Track
              </Button>
            </div>
          )}
        </div>

        {/* Feature Cards */}
        <div className="grid md:grid-cols-3 gap-6 mt-16 max-w-6xl mx-auto">
          <div className="bg-gray-900 p-6 rounded-lg border border-gray-800">
            <Users className="h-12 w-12 text-blue-400 mb-4" />
            <h3 className="text-xl font-semibold mb-2">Crowdsourced Content</h3>
            <p className="text-gray-400">
              Discover music from independent artists and creators from around the world
            </p>
          </div>
          <div className="bg-gray-900 p-6 rounded-lg border border-gray-800">
            <Upload className="h-12 w-12 text-green-400 mb-4" />
            <h3 className="text-xl font-semibold mb-2">Easy Upload</h3>
            <p className="text-gray-400">
              Upload your tracks instantly with automatic music analysis and tagging
            </p>
          </div>
          <div className="bg-gray-900 p-6 rounded-lg border border-gray-800">
            <Music className="h-12 w-12 text-purple-400 mb-4" />
            <h3 className="text-xl font-semibold mb-2">High Quality Audio</h3>
            <p className="text-gray-400">
              Support for multiple audio formats with detailed musical analysis
            </p>
          </div>
        </div>
      </div>

      {/* Music Library Section */}
      <div className="flex-1 px-6 pb-12">
        <div className="max-w-7xl mx-auto">
          <h2 className="text-3xl font-bold mb-8 text-center">
            🎵 Community Music Library
          </h2>
          <AudioLibrary />
        </div>
      </div>

      {/* Auth Modal */}
      <AuthModal
        isOpen={authModalOpen}
        onClose={() => setAuthModalOpen(false)}
        defaultMode="register"
      />
    </main>
  );
}
