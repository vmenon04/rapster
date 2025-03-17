// AudioLibrary.tsx
import { useEffect, useState, useRef } from "react";
import { fetchAudioFiles } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Play, Pause, Music } from "lucide-react";
import { AnalyticsModal } from "@/components/AnalyticsModal";

interface AudioFile {
  id: number;
  title: string;
  artist: string;
  file_url: string;
  image_url?: string;
}

export default function AudioLibrary() {
  const [audioFiles, setAudioFiles] = useState<AudioFile[]>([]);
  const [currentAudioIndex, setCurrentAudioIndex] = useState<number | null>(null);
  const [selectedFile, setSelectedFile] = useState<AudioFile | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);

  // Shared audio element and context refs
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);

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

  const setupAudio = (audio: HTMLAudioElement) => {
    audio.addEventListener("loadedmetadata", () => {
      setDuration(audio.duration);
    });
    audio.addEventListener("timeupdate", () => {
      setCurrentTime(audio.currentTime);
    });
    if (!audioContextRef.current) {
      const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
      audioContextRef.current = new AudioContextClass();
    }
    if (audioContextRef.current) {
      try {
        const source = audioContextRef.current.createMediaElementSource(audio);
        const analyser = audioContextRef.current.createAnalyser();
        analyser.fftSize = 2048;
        source.connect(analyser);
        analyser.connect(audioContextRef.current.destination);
        analyserRef.current = analyser;
      } catch (e) {
        console.error("Error setting up audio context:", e);
      }
    }
  };

  const handlePlayPause = (file: AudioFile, index: number) => {
    if (currentAudioIndex === index) {
      if (audioRef.current) {
        if (audioRef.current.paused) {
          if (audioContextRef.current && audioContextRef.current.state === "suspended") {
            audioContextRef.current.resume();
          }
          audioRef.current
            .play()
            .then(() => setIsPlaying(true))
            .catch((err) => console.error("Play error:", err));
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
      newAudio.crossOrigin = "anonymous";
      audioRef.current = newAudio;
      setupAudio(newAudio);
      if (audioContextRef.current && audioContextRef.current.state === "suspended") {
        audioContextRef.current.resume();
      }
      newAudio
        .play()
        .then(() => setIsPlaying(true))
        .catch((err) => console.error("Error playing audio:", err));
      setCurrentAudioIndex(index);
    }
  };

  const togglePlayPause = () => {
    if (audioRef.current) {
      if (audioRef.current.paused) {
        if (audioContextRef.current && audioContextRef.current.state === "suspended") {
          audioContextRef.current.resume();
        }
        audioRef.current
          .play()
          .then(() => setIsPlaying(true))
          .catch((err) => console.error("Play error:", err));
      } else {
        audioRef.current.pause();
        setIsPlaying(false);
      }
    }
  };

  return (
    <div className="w-full max-w-4xl mx-auto p-4">
      <div className="bg-white rounded-md shadow overflow-hidden">
        <div className="px-4 py-4 border-b flex items-center justify-between">
          <h1 className="text-lg font-semibold">Your Library</h1>
        </div>
        {audioFiles.map((file, index) => (
          <div
            key={file.id}
            className={`flex items-center p-4 border-b last:border-b-0 hover:bg-gray-50 transition cursor-pointer fade-in-up`}
            style={{ animationDelay: `${index * 0.1}s` }}
            onClick={() => {
              setSelectedFile(file);
              if (currentAudioIndex !== index) {
                handlePlayPause(file, index);
              }
            }}
          >
            <div className="w-10 h-10 flex-shrink-0 rounded-md overflow-hidden bg-gray-200 flex items-center justify-center mr-3">
              {file.image_url ? (
                <img src={file.image_url} alt={file.title} className="w-full h-full object-cover" />
              ) : (
                <Music className="w-5 h-5 text-gray-500" />
              )}
            </div>
            <div className="flex-1">
              <div className="font-medium text-sm text-gray-900 truncate">{file.title}</div>
              <div className="text-xs text-gray-500">{file.artist || "Unknown Artist"}</div>
            </div>
            <Button
              variant="ghost"
              size="icon"
              onClick={(e) => {
                e.stopPropagation();
                handlePlayPause(file, index);
              }}
            >
              {currentAudioIndex === index && isPlaying ? (
                <Pause className="w-4 h-4" />
              ) : (
                <Play className="w-4 h-4" />
              )}
            </Button>
          </div>
        ))}
      </div>

      {selectedFile && (
        <AnalyticsModal
          file={selectedFile}
          onClose={() => setSelectedFile(null)}
          isPlaying={isPlaying}
          togglePlayPause={togglePlayPause}
          currentTime={currentTime}
          duration={duration}
          analyser={analyserRef.current}
          audioRef={audioRef}
          setCurrentTime={setCurrentTime}
        />
      )}
    </div>
  );
}
