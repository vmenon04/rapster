"use client";

import { useEffect, useState, useRef } from "react";
import { fetchAudioFiles } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Play, Pause, Music } from "lucide-react";

// Define the audio file structure
interface AudioFile {
  id: number;
  title: string;
  artist: string;
  file_url: string;
  image_url?: string;
}

export default function AudioLibrary() {
  const [audioFiles, setAudioFiles] = useState<AudioFile[]>([]);
  const [currentAudio, setCurrentAudio] = useState<number | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    async function getAudioFiles() {
      try {
        const files: AudioFile[] = await fetchAudioFiles();
        setAudioFiles(files);
      } catch (error) {
        console.error("Failed to fetch audio files", error);
      }
    }
    getAudioFiles();
  }, []);

  const handlePlayPause = (file: AudioFile, index: number) => {
    if (currentAudio === index) {
      if (audioRef.current) {
        if (audioRef.current.paused) {
          audioRef.current.play();
          setIsPlaying(true);
        } else {
          audioRef.current.pause();
          setIsPlaying(false);
        }
      }
    } else {
      if (audioRef.current) {
        audioRef.current.pause();
      }
      const newAudio = new Audio(file.file_url);
      audioRef.current = newAudio;
      audioRef.current.play();
      setCurrentAudio(index);
      setIsPlaying(true);
    }
  };

  return (
    <div className="h-screen w-full flex flex-col items-center p-6 overflow-y-auto">
      <h1 className="text-2xl font-bold mb-4">Song List</h1>
      
      {/* 🔹 Song List with Scrollable Content */}
      <div className="w-full max-w-lg max-h-[75vh] overflow-y-auto space-y-2">
        {audioFiles.map((file, index) => (
          <Card
            key={file.id}
            className="flex items-center p-2 border border-gray-300 rounded-md transition cursor-pointer hover:shadow-md"
            onClick={() => handlePlayPause(file, index)}
          >
            {/* Album Art */}
            <div className="w-12 h-12 flex-shrink-0 rounded-md overflow-hidden bg-gray-200 flex items-center justify-center">
              {file.image_url ? (
                <img src={file.image_url} alt={file.title} className="object-cover w-full h-full" />
              ) : (
                <Music className="w-6 h-6 text-gray-500" />
              )}
            </div>

            {/* Song Info */}
            <div className="flex-1 mx-3 min-w-0">
              <div className="text-sm font-medium text-gray-900 truncate">{file.title}</div>
              <div className="text-xs text-gray-500">{file.artist || "Unknown Artist"}</div>
            </div>

            {/* Play/Pause Button */}
            <Button variant="ghost" size="icon">
              {currentAudio === index && isPlaying ? (
                <Pause className="w-4 h-4 text-gray-800" />
              ) : (
                <Play className="w-4 h-4 text-gray-800" />
              )}
            </Button>
          </Card>
        ))}
      </div>
    </div>
  );
}
