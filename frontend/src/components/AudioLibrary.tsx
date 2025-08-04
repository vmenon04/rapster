// AudioLibrary.tsx
import { useEffect, useState, useRef, useCallback } from "react";
import { Play, Pause, Music, Loader2, AlertCircle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { AnalyticsModal } from "@/components/AnalyticsModal";
import { apiClient, AudioFile } from "@/lib/api";
import { handleError, showErrorToast } from "@/lib/errors";
import { useAsync } from "@/hooks/useAsync";
import { config } from "@/lib/config";
import Hls from "hls.js";

export default function AudioLibrary() {
  const [audioFiles, setAudioFiles] = useState<AudioFile[]>([]);
  const [currentAudioIndex, setCurrentAudioIndex] = useState<number | null>(null);
  const [selectedFile, setSelectedFile] = useState<AudioFile | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [currentQuality, setCurrentQuality] = useState<string>('auto');

  // Shared audio element and context refs
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const hlsRef = useRef<Hls | null>(null);

  // Use async hook for data fetching
  const { data: files, isLoading, error, execute: fetchFiles } = useAsync<AudioFile[]>();

  const loadAudioFiles = useCallback(async () => {
    try {
      await fetchFiles(() => apiClient.getAudioFiles());
    } catch (error) {
      const appError = handleError(error, 'audio library');
      showErrorToast(appError, 'Failed to load audio files');
    }
  }, [fetchFiles]);

  useEffect(() => {
    loadAudioFiles();
  }, [loadAudioFiles]);

  useEffect(() => {
    if (files) {
      setAudioFiles(files);
    }
  }, [files]);

  // Cleanup HLS instance on component unmount
  useEffect(() => {
    return () => {
      if (hlsRef.current) {
        hlsRef.current.destroy();
        hlsRef.current = null;
      }
    };
  }, []);

  const setupAudio = (audio: HTMLAudioElement) => {
    // Remove existing event listeners to prevent duplicates
    audio.removeEventListener("loadedmetadata", handleLoadedMetadata);
    audio.removeEventListener("timeupdate", handleTimeUpdate);
    audio.removeEventListener("ended", handleAudioEnded);

    // Add event listeners
    audio.addEventListener("loadedmetadata", handleLoadedMetadata);
    audio.addEventListener("timeupdate", handleTimeUpdate);
    audio.addEventListener("ended", handleAudioEnded);

    // Set up audio context and analyser
    if (!audioContextRef.current) {
      const AudioContextClass = window.AudioContext || (window as typeof window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
      if (AudioContextClass) {
        audioContextRef.current = new AudioContextClass();
      }
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

  const setupHLSPlayer = useCallback((audioElement: HTMLAudioElement, hlsUrl: string) => {
    // Clean up existing HLS instance
    if (hlsRef.current) {
      hlsRef.current.destroy();
      hlsRef.current = null;
    }

    if (Hls.isSupported()) {
      const hls = new Hls({
        // Auto quality selection
        startLevel: -1,
        // Progressive enhancement
        enableWorker: true,
        lowLatencyMode: false,
      });
      
      hls.loadSource(hlsUrl);
      hls.attachMedia(audioElement);
      
      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        console.log('HLS manifest loaded, available qualities:', hls.levels);
      });
      
      hls.on(Hls.Events.LEVEL_SWITCHED, (event, data) => {
        const level = hls.levels[data.level];
        console.log('Quality switched to:', level);
        setCurrentQuality(level.name || `${Math.round(level.bitrate / 1000)}kbps`);
      });

      hls.on(Hls.Events.ERROR, (event, data) => {
        console.error('HLS error:', data);
        if (data.fatal) {
          switch (data.type) {
            case Hls.ErrorTypes.NETWORK_ERROR:
              console.log('Fatal network error encountered, trying to recover');
              hls.startLoad();
              break;
            case Hls.ErrorTypes.MEDIA_ERROR:
              console.log('Fatal media error encountered, trying to recover');
              hls.recoverMediaError();
              break;
            default:
              console.log('Fatal error, cannot recover');
              hls.destroy();
              break;
          }
        }
      });
      
      hlsRef.current = hls;
      return hls;
    } else if (audioElement.canPlayType('application/vnd.apple.mpegurl')) {
      // Native HLS support (Safari)
      audioElement.src = hlsUrl;
      setCurrentQuality('auto (native)');
      return null;
    } else {
      // Fallback to regular audio
      console.warn('HLS not supported, falling back to standard audio');
      return null;
    }
  }, []);

  const getOptimalAudioUrl = (file: AudioFile): { url: string; isHLS: boolean; quality?: string } => {
    // Prefer HLS for adaptive streaming
    if (file.hls_url) {
      return { url: file.hls_url, isHLS: true };
    }
    
    // Check for multiple format support
    if (file.file_urls && Object.keys(file.file_urls).length > 0) {
      // Prefer medium quality, fallback to high, then low
      const preferredOrder = ['medium', 'high', 'low'];
      for (const quality of preferredOrder) {
        if (file.file_urls[quality]) {
          return { url: file.file_urls[quality], isHLS: false, quality };
        }
      }
      
      // If no preferred quality, take the first available
      const firstQuality = Object.keys(file.file_urls)[0];
      return { url: file.file_urls[firstQuality], isHLS: false, quality: firstQuality };
    }
    
    // Fallback to original file URL
    return { url: file.file_url, isHLS: false, quality: 'original' };
  };

  const handleLoadedMetadata = () => {
    if (audioRef.current) {
      setDuration(audioRef.current.duration);
    }
  };

  const handleTimeUpdate = () => {
    if (audioRef.current) {
      setCurrentTime(audioRef.current.currentTime);
    }
  };

  const handleAudioEnded = () => {
    setIsPlaying(false);
    setCurrentTime(0);
  };

  const handlePlayPause = async (file: AudioFile, index: number) => {
    try {
      if (currentAudioIndex === index && audioRef.current) {
        // Same file - toggle play/pause
        if (audioRef.current.paused) {
          if (audioContextRef.current && audioContextRef.current.state === "suspended") {
            await audioContextRef.current.resume();
          }
          await audioRef.current.play();
          setIsPlaying(true);
        } else {
          audioRef.current.pause();
          setIsPlaying(false);
        }
      } else {
        // Different file - stop current and play new
        if (audioRef.current) {
          audioRef.current.pause();
          audioRef.current.currentTime = 0;
        }

        // Clean up existing HLS instance
        if (hlsRef.current) {
          hlsRef.current.destroy();
          hlsRef.current = null;
        }

        // Get optimal audio URL
        const { url: audioUrl, isHLS, quality } = getOptimalAudioUrl(file);
        console.log(`Playing ${file.title} - URL: ${audioUrl}, HLS: ${isHLS}, Quality: ${quality}`);

        // Create new audio element
        const newAudio = new Audio();
        newAudio.crossOrigin = "anonymous";
        newAudio.volume = config.player.defaultVolume;
        
        if (isHLS) {
          // Setup HLS streaming
          setupHLSPlayer(newAudio, audioUrl);
        } else {
          // Regular audio file
          newAudio.src = audioUrl;
          setCurrentQuality(quality || 'original');
        }
        
        audioRef.current = newAudio;
        setupAudio(newAudio);

        // Resume audio context if suspended
        if (audioContextRef.current && audioContextRef.current.state === "suspended") {
          await audioContextRef.current.resume();
        }

        try {
          await newAudio.play();
          setIsPlaying(true);
          setCurrentAudioIndex(index);
        } catch (playError) {
          console.error("Error playing audio:", playError);
          showErrorToast({ message: "Failed to play audio file" }, "Playback error");
          setIsPlaying(false);
        }
      }
    } catch (error) {
      console.error("Error in handlePlayPause:", error);
      const appError = handleError(error, 'audio playback');
      showErrorToast(appError, 'Failed to play audio');
      setIsPlaying(false);
    }
  };

  const togglePlayPause = async () => {
    if (audioRef.current) {
      try {
        if (audioRef.current.paused) {
          if (audioContextRef.current && audioContextRef.current.state === "suspended") {
            await audioContextRef.current.resume();
          }
          await audioRef.current.play();
          setIsPlaying(true);
        } else {
          audioRef.current.pause();
          setIsPlaying(false);
        }
      } catch (error) {
        console.error("Error toggling playback:", error);
        showErrorToast({ message: "Playback control failed" }, "Audio error");
      }
    }
  };

  const formatTime = (time: number): string => {
    if (isNaN(time)) return "0:00";
    const minutes = Math.floor(time / 60);
    const seconds = Math.floor(time % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  const formatDuration = (seconds?: number): string => {
    if (!seconds) return "";
    return formatTime(seconds);
  };

  const getFileDisplayInfo = (file: AudioFile) => {
    const features = [];
    if (file.bpm) features.push(`${Math.round(file.bpm)} BPM`);
    if (file.key && file.scale) features.push(`${file.key} ${file.scale}`);
    if (file.duration_sec) features.push(formatDuration(file.duration_sec));
    
    // Add streaming info
    if (file.hls_url) {
      features.push("HLS");
    } else if (file.file_urls && Object.keys(file.file_urls).length > 0) {
      features.push(`${Object.keys(file.file_urls).length} qualities`);
    }
    
    return features.join(" • ");
  };

  const getStreamingStatusIcon = (file: AudioFile) => {
    if (file.hls_url) {
      return <span className="text-green-600 text-xs" title="Adaptive streaming available">📡</span>;
    } else if (file.file_urls && Object.keys(file.file_urls).length > 0) {
      return <span className="text-blue-600 text-xs" title="Multiple qualities available">🎚️</span>;
    }
    return null;
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="w-full max-w-4xl mx-auto p-4">
        <div className="bg-white rounded-md shadow overflow-hidden">
          <div className="px-4 py-4 border-b flex items-center justify-center">
            <Loader2 className="w-6 h-6 animate-spin mr-2" />
            <span>Loading your music library...</span>
          </div>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="w-full max-w-4xl mx-auto p-4">
        <div className="bg-white rounded-md shadow overflow-hidden">
          <div className="px-4 py-8 text-center">
            <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Failed to load library</h3>
            <p className="text-gray-600 mb-4">{error}</p>
            <Button onClick={loadAudioFiles} variant="outline">
              <RefreshCw className="w-4 h-4 mr-2" />
              Try Again
            </Button>
          </div>
        </div>
      </div>
    );
  }

  // Empty state
  if (audioFiles.length === 0) {
    return (
      <div className="w-full max-w-4xl mx-auto p-4">
        <div className="bg-white rounded-md shadow overflow-hidden">
          <div className="px-4 py-4 border-b flex items-center justify-between">
            <h1 className="text-lg font-semibold">Your Library</h1>
            <Button onClick={loadAudioFiles} variant="outline" size="sm">
              <RefreshCw className="w-4 h-4 mr-2" />
              Refresh
            </Button>
          </div>
          <div className="px-4 py-8 text-center">
            <Music className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-900 mb-2">No music yet</h3>
            <p className="text-gray-600">Upload your first track to get started!</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full max-w-4xl mx-auto p-4">
      <div className="bg-white rounded-md shadow overflow-hidden">
        <div className="px-4 py-4 border-b flex items-center justify-between">
          <h1 className="text-lg font-semibold">Your Library ({audioFiles.length} tracks)</h1>
          <Button onClick={loadAudioFiles} variant="outline" size="sm">
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
        </div>
        
        {audioFiles.map((file, index) => (
          <div
            key={file.id}
            className={`flex items-center p-4 border-b last:border-b-0 hover:bg-gray-50 transition cursor-pointer fade-in-up ${
              currentAudioIndex === index ? 'bg-blue-50 border-blue-200' : ''
            }`}
            style={{ animationDelay: `${index * 0.1}s` }}
            onClick={() => {
              setSelectedFile(file);
              if (currentAudioIndex !== index) {
                handlePlayPause(file, index);
              }
            }}
          >
            {/* Album Art */}
            <div className="w-12 h-12 flex-shrink-0 rounded-md overflow-hidden bg-gray-200 flex items-center justify-center mr-4">
              {file.image_url ? (
                <img 
                  src={file.image_url} 
                  alt={file.title} 
                  className="w-full h-full object-cover"
                  onError={(e) => {
                    const target = e.target as HTMLImageElement;
                    target.style.display = 'none';
                    target.nextElementSibling?.classList.remove('hidden');
                  }}
                />
              ) : null}
              <Music className={`w-6 h-6 text-gray-500 ${file.image_url ? 'hidden' : ''}`} />
            </div>

            {/* Track Info */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <div className="font-medium text-sm text-gray-900 truncate">{file.title}</div>
                {getStreamingStatusIcon(file)}
                {currentAudioIndex === index && currentQuality !== 'auto' && (
                  <span className="text-xs bg-blue-100 text-blue-700 px-1 rounded">
                    {currentQuality}
                  </span>
                )}
              </div>
              <div className="text-xs text-gray-500 truncate">{file.artist || "Unknown Artist"}</div>
              {file.uploader_username && (
                <div className="text-xs text-blue-600 truncate">
                  Uploaded by @{file.uploader_username}
                </div>
              )}
              {getFileDisplayInfo(file) && (
                <div className="text-xs text-gray-400 mt-1">{getFileDisplayInfo(file)}</div>
              )}
            </div>

            {/* Play/Pause Button */}
            <Button
              variant="ghost"
              size="icon"
              onClick={(e) => {
                e.stopPropagation();
                handlePlayPause(file, index);
              }}
              className={`ml-2 ${currentAudioIndex === index && isPlaying ? 'text-blue-600' : ''}`}
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
