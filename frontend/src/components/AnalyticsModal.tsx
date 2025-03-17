"use client";

import { useEffect, useState, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Play, Pause, Music } from "lucide-react";
import { ScrubbableWaveform } from "@/components/ScrubbableWaveform";

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

export function AnalyticsModal({
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

  // Refs for your original time-domain & frequency canvases
  const waveformCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const freqCanvasRef = useRef<HTMLCanvasElement | null>(null);

  // Animation frame IDs
  const animationFrameRef = useRef<number | null>(null);

  useEffect(() => {
    // Animate the modal in
    setAnimate(true);
  }, []);

  // Keep your original draw code for the two canvases
  useEffect(() => {
    const drawVisualizations = () => {
      if (analyser) {
        // 1) Live Oscilloscope (time-domain)
        if (waveformCanvasRef.current) {
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

        // 2) Frequency distribution
        if (freqCanvasRef.current) {
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
      }

      animationFrameRef.current = requestAnimationFrame(drawVisualizations);
    };

    drawVisualizations();
    return () => {
      if (animationFrameRef.current) cancelAnimationFrame(animationFrameRef.current);
    };
  }, [analyser]);

  // Utility to format time
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
      {/* Modal content (scrollable if needed) */}
      <div
        className={`relative bg-white p-6 md:p-8 rounded-md shadow-lg max-w-4xl w-full max-h-[80vh] overflow-y-auto transform transition-all duration-300 ${
          animate ? "opacity-100 scale-100" : "opacity-0 scale-95"
        }`}
      >
        <div className="flex flex-col md:flex-row">
          {/* Cover Art */}
          <div className="md:w-1/3 flex-shrink-0 flex items-center justify-center mb-4 md:mb-0">
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
          <div className="md:w-2/3 md:pl-6 flex flex-col space-y-6">
            <div>
              <h2 className="text-xl md:text-2xl font-bold mb-2">
                Analytics for {file.title}
              </h2>
            </div>

            {/* Playback + Scrubbable Waveform */}
            <div>
              <div className="flex items-center space-x-4 mb-2">
                <Button onClick={togglePlayPause} size="sm">
                  {isPlaying ? (
                    <Pause className="w-4 h-4" />
                  ) : (
                    <Play className="w-4 h-4" />
                  )}
                </Button>
                <div className="flex-1 h-12">
                  <ScrubbableWaveform
                    audioUrl={file.file_url}
                    currentTime={currentTime}
                    duration={duration}
                    onScrub={(newTime) => {
                      setCurrentTime(newTime);
                      if (audioRef.current) {
                        audioRef.current.currentTime = newTime;
                      }
                    }}
                    className="w-full h-full"
                  />
                </div>
              </div>
              <div className="flex justify-between text-sm text-gray-600">
                <span>{formatTime(currentTime)}</span>
                <span>{formatTime(duration)}</span>
              </div>
            </div>

            {/* Waveform Visualizer (time-domain) */}
            <div className="w-full h-24 bg-gray-100 rounded-md overflow-hidden">
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
