"use client";

import { useEffect, useState, useRef } from "react";
import { fetchAudioFiles } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Play, Pause, Music } from "lucide-react";

interface AudioFile {
  id: number;
  title: string;
  artist: string;
  file_url: string;
  image_url?: string;
}

interface AnalyticsModalProps {
  file: AudioFile;
  onClose: () => void;
  isPlaying: boolean;
  togglePlayPause: () => void;
  currentTime: number;
  duration: number;
  analyser: AnalyserNode | null;
  audioRef: React.RefObject<HTMLAudioElement | null>;
  setCurrentTime: (time: number) => void;
}

function AnalyticsModal({
  file,
  onClose,
  isPlaying,
  togglePlayPause,
  currentTime,
  duration,
  analyser,
  audioRef,
  setCurrentTime,
}: AnalyticsModalProps) {
  const [animate, setAnimate] = useState(false);
  const waveformCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const freqCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const animationFrameRef = useRef<number | null>(null);

  useEffect(() => {
    // Animate the modal in
    setAnimate(true);
  }, []);

  useEffect(() => {
    const drawVisualizations = () => {
      // Waveform visualization
      if (analyser && waveformCanvasRef.current) {
        const canvas = waveformCanvasRef.current;
        const ctx = canvas.getContext("2d");
        if (ctx) {
          const bufferLength = analyser.frequencyBinCount;
          const dataArray = new Uint8Array(bufferLength);
          analyser.getByteTimeDomainData(dataArray);
          const { width, height } = canvas;
          ctx.clearRect(0, 0, width, height);
          ctx.lineWidth = 2;
          ctx.strokeStyle = "#4A5568"; // gray-700
          ctx.beginPath();
          const sliceWidth = width / bufferLength;
          let x = 0;
          for (let i = 0; i < bufferLength; i++) {
            const v = dataArray[i] / 128.0;
            const y = (v * height) / 2;
            if (i === 0) {
              ctx.moveTo(x, y);
            } else {
              ctx.lineTo(x, y);
            }
            x += sliceWidth;
          }
          ctx.lineTo(width, height / 2);
          ctx.stroke();
        }
      }

      // Frequency distribution visualization
      if (analyser && freqCanvasRef.current) {
        const canvas = freqCanvasRef.current;
        const ctx = canvas.getContext("2d");
        if (ctx) {
          const bufferLength = analyser.frequencyBinCount;
          const dataArray = new Uint8Array(bufferLength);
          analyser.getByteFrequencyData(dataArray);
          const { width, height } = canvas;
          ctx.clearRect(0, 0, width, height);

          const barWidth = (width / bufferLength) * 2.5;
          let x = 0;
          for (let i = 0; i < bufferLength; i++) {
            const barHeight = (dataArray[i] / 255) * height;
            ctx.fillStyle = "#4A5568"; // gray-700
            ctx.fillRect(x, height - barHeight, barWidth, barHeight);
            x += barWidth + 1;
          }
        }
      }

      animationFrameRef.current = requestAnimationFrame(drawVisualizations);
    };

    drawVisualizations();
    return () => {
      if (animationFrameRef.current) cancelAnimationFrame(animationFrameRef.current);
    };
  }, [analyser]);

  const formatTime = (time: number) => {
    const minutes = Math.floor(time / 60);
    const seconds = Math.floor(time % 60).toString().padStart(2, "0");
    return `${minutes}:${seconds}`;
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Dimmed backdrop */}
      <div
        className="absolute inset-0 bg-black opacity-50 transition-opacity"
        onClick={onClose}
      />
      {/* Modal content */}
      <div
        className={`relative bg-white p-8 rounded-md shadow-lg max-w-4xl w-full transform transition-all duration-300 ${
          animate ? "opacity-100 scale-100" : "opacity-0 scale-95"
        }`}
      >
        <div className="flex flex-col md:flex-row">
          {/* Cover Art */}
          <div className="md:w-1/3 flex-shrink-0 flex items-center justify-center">
            {file.image_url ? (
              <img
                src={file.image_url}
                alt={file.title}
                className="w-full h-auto rounded-md"
              />
            ) : (
              <div className="w-32 h-32 bg-gray-200 flex items-center justify-center rounded-md">
                <Music className="w-12 h-12 text-gray-500" />
              </div>
            )}
          </div>
          {/* Controls and Visualizers */}
          <div className="md:w-2/3 mt-4 md:mt-0 md:pl-6">
            <h2 className="text-2xl font-bold mb-4">Analytics for {file.title}</h2>
            {/* Playback Controls */}
            <div className="flex items-center space-x-4 mb-4">
              <Button onClick={togglePlayPause} size="sm">
                {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
              </Button>
              <input
                type="range"
                min={0}
                max={duration}
                step="0.1"
                value={currentTime}
                onChange={(e) => {
                  const newTime = Number(e.target.value);
                  setCurrentTime(newTime);
                  if (audioRef.current) {
                    audioRef.current.currentTime = newTime;
                  }
                }}
                className="range-gray w-full" // <-- apply our custom gray styling
              />
            </div>
            <div className="flex justify-between text-sm text-gray-600 mb-4">
              <span>{formatTime(currentTime)}</span>
              <span>{formatTime(duration)}</span>
            </div>
            {/* Waveform Visualizer */}
            <div className="w-full h-24 bg-gray-100 rounded-md overflow-hidden mb-4">
              <canvas
                ref={waveformCanvasRef}
                width={600}
                height={100}
                className="w-full h-full"
              />
            </div>
            {/* Frequency Distribution Visualizer */}
            <div className="w-full h-24 bg-gray-100 rounded-md overflow-hidden">
              <canvas
                ref={freqCanvasRef}
                width={600}
                height={100}
                className="w-full h-full"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
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

  // Setup the audio element with event listeners and connect it to the analyser
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

  // Handle play/pause from the list
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

  // Toggle playback (used in both list and modal)
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
        {/* Optional heading */}
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
            {/* Cover Art / Icon */}
            <div className="w-10 h-10 flex-shrink-0 rounded-md overflow-hidden bg-gray-200 flex items-center justify-center mr-3">
              {file.image_url ? (
                <img src={file.image_url} alt={file.title} className="w-full h-full object-cover" />
              ) : (
                <Music className="w-5 h-5 text-gray-500" />
              )}
            </div>

            {/* Song Info */}
            <div className="flex-1">
              <div className="font-medium text-sm text-gray-900 truncate">{file.title}</div>
              <div className="text-xs text-gray-500">{file.artist || "Unknown Artist"}</div>
            </div>

            {/* Play/Pause Button */}
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

      {/* Analytics Modal */}
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
