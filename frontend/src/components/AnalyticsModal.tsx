"use client";

import { useEffect, useState, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Play, Pause, Music, X } from "lucide-react";
import { ScrubbableWaveform } from "@/components/ScrubbableWaveform";
import { AudioFile } from "@/lib/api";

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

  const waveformCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const freqCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const animationFrameRef = useRef<number | null>(null);

  useEffect(() => {
    setAnimate(true);
  }, []);

  useEffect(() => {
    const drawVisualizations = () => {
      if (analyser) {
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
            ctx.strokeStyle = "#4A5568";
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
              ctx.fillStyle = "#4A5568";
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

  const formatTime = (time: number) => {
    if (isNaN(time)) return "0:00";
    const minutes = Math.floor(time / 60);
    const seconds = Math.floor(time % 60).toString().padStart(2, "0");
    return `${minutes}:${seconds}`;
  };

  // Handle escape key to close modal
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div
        className="absolute inset-0 bg-black opacity-50 transition-opacity"
        onClick={onClose}
      />
      <div
        className={`relative bg-white p-6 md:p-8 rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto transform transition-all duration-300 ${
          animate ? "opacity-100 scale-100" : "opacity-0 scale-95"
        }`}
      >
        {/* Close Button */}
        <Button
          variant="ghost"
          size="icon"
          onClick={onClose}
          className="absolute top-4 right-4 z-10"
        >
          <X className="w-4 h-4" />
        </Button>
        <div className="flex flex-col md:flex-row">
          {/* Cover Art */}
          <div className="md:w-1/3 flex-shrink-0 flex items-center justify-center mb-6 md:mb-0">
            {file.image_url ? (
              <img
                src={file.image_url}
                alt={file.title}
                className="w-full max-w-sm h-auto rounded-lg shadow-sm"
                onError={(e) => {
                  const target = e.target as HTMLImageElement;
                  target.style.display = 'none';
                  target.nextElementSibling?.classList.remove('hidden');
                }}
              />
            ) : null}
            <div className={`w-48 h-48 bg-gray-200 flex items-center justify-center rounded-lg ${file.image_url ? 'hidden' : ''}`}>
              <Music className="w-16 h-16 text-gray-500" />
            </div>
          </div>

          {/* Right Section */}
          <div className="md:w-2/3 md:pl-8 flex flex-col space-y-6">
            {/* Header */}
            <div>
              <h2 className="text-2xl md:text-3xl font-bold text-gray-900 mb-1">
                {file.title}
              </h2>
              <p className="text-lg text-gray-600">
                {file.artist || "Unknown Artist"}
              </p>
            </div>

            {/* Playback + Waveform */}
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

            {/* Audio Features Grid */}
            <div className="w-full">
              <h3 className="text-lg font-semibold mb-3 text-gray-800">Audio Features</h3>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                {typeof file.bpm === 'number' && !isNaN(file.bpm) && (
                  <div className="bg-gray-50 p-3 rounded-lg">
                    <div className="text-sm text-gray-600">BPM</div>
                    <div className="text-lg font-semibold text-gray-900">{file.bpm.toFixed(1)}</div>
                  </div>
                )}
                {file.key && (
                  <div className="bg-gray-50 p-3 rounded-lg">
                    <div className="text-sm text-gray-600">Key</div>
                    <div className="text-lg font-semibold text-gray-900">{file.key} {file.scale || ""}</div>
                  </div>
                )}
                {typeof file.key_strength === 'number' && !isNaN(file.key_strength) && (
                  <div className="bg-gray-50 p-3 rounded-lg">
                    <div className="text-sm text-gray-600">Key Strength</div>
                    <div className="text-lg font-semibold text-gray-900">{file.key_strength.toFixed(2)}</div>
                  </div>
                )}
                {typeof file.loudness === 'number' && !isNaN(file.loudness) && (
                  <div className="bg-gray-50 p-3 rounded-lg">
                    <div className="text-sm text-gray-600">Loudness</div>
                    <div className="text-lg font-semibold text-gray-900">{file.loudness.toFixed(1)} LUFS</div>
                  </div>
                )}
                {typeof file.danceability === 'number' && !isNaN(file.danceability) && (
                  <div className="bg-gray-50 p-3 rounded-lg">
                    <div className="text-sm text-gray-600">Danceability</div>
                    <div className="text-lg font-semibold text-gray-900">{file.danceability.toFixed(2)}</div>
                  </div>
                )}
                {file.duration_sec !== undefined && (
                  <div className="bg-gray-50 p-3 rounded-lg">
                    <div className="text-sm text-gray-600">Duration</div>
                    <div className="text-lg font-semibold text-gray-900">{formatTime(file.duration_sec)}</div>
                  </div>
                )}
              </div>
            </div>

            {/* Real-time Visualizations */}
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-gray-800">Live Audio Analysis</h3>
              
              {/* Waveform Canvas */}
              <div className="w-full">
                <div className="text-sm text-gray-600 mb-2">Waveform</div>
                <div className="w-full h-24 bg-gray-100 rounded-lg overflow-hidden border">
                  <canvas
                    ref={waveformCanvasRef}
                    width={600}
                    height={96}
                    className="w-full h-full"
                  />
                </div>
              </div>

              {/* Frequency Canvas */}
              <div className="w-full">
                <div className="text-sm text-gray-600 mb-2">Frequency Spectrum</div>
                <div className="w-full h-24 bg-gray-100 rounded-lg overflow-hidden border">
                  <canvas
                    ref={freqCanvasRef}
                    width={600}
                    height={96}
                    className="w-full h-full"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
