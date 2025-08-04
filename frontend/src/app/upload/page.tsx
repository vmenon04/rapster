"use client";

import { useState, useRef, useEffect } from "react";
import { Upload, Image as ImageIcon, AlertCircle, CheckCircle, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { useRouter } from "next/navigation";
import { apiClient } from "@/lib/api";
import { handleError, showErrorToast } from "@/lib/errors";
import { useAsyncOperation } from "@/hooks/useAsync";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { config } from "@/lib/config";

type Step = "INITIAL" | "DETAILS" | "UPLOADING" | "SUCCESS";

interface UploadProgress {
  step: string;
  percentage: number;
  message: string;
}

export default function UploadPage() {
  const [step, setStep] = useState<Step>("INITIAL");
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [artist, setArtist] = useState("");
  const [trackTitle, setTrackTitle] = useState("");
  const [coverImage, setCoverImage] = useState<File | null>(null);
  const [uploadProgress, setUploadProgress] = useState<UploadProgress>({
    step: "",
    percentage: 0,
    message: "",
  });

  const { execute: executeUpload, isLoading: isUploading, error: uploadError } = useAsyncOperation();
  const audioInputRef = useRef<HTMLInputElement | null>(null);
  const coverImageRef = useRef<HTMLInputElement | null>(null);
  const router = useRouter();

  // Validation functions
  const validateAudioFile = (file: File): string | null => {
    if (file.size > config.upload.maxFileSize) {
      return `File size exceeds maximum allowed size of ${config.upload.maxFileSize / (1024 * 1024)}MB`;
    }

    const fileExt = `.${file.name.split('.').pop()?.toLowerCase()}`;
    if (!config.upload.allowedAudioFormats.includes(fileExt as ".mp3" | ".wav" | ".flac" | ".aac" | ".ogg")) {
      return `Invalid audio format. Allowed formats: ${config.upload.allowedAudioFormats.join(', ')}`;
    }

    return null;
  };

  const validateImageFile = (file: File): string | null => {
    const fileExt = `.${file.name.split('.').pop()?.toLowerCase()}`;
    if (!config.upload.allowedImageFormats.includes(fileExt as ".jpg" | ".jpeg" | ".png" | ".webp")) {
      return `Invalid image format. Allowed formats: ${config.upload.allowedImageFormats.join(', ')}`;
    }

    if (file.size > 10 * 1024 * 1024) { // 10MB limit for images
      return "Image size must be under 10MB";
    }

    return null;
  };

  // File selection handlers
  const handleAudioChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    
    const file = e.target.files[0];
    const validationError = validateAudioFile(file);
    
    if (validationError) {
      toast.error(validationError);
      return;
    }

    setAudioFile(file);
    
    // Auto-fill title from filename if not already set
    if (!trackTitle) {
      const nameWithoutExt = file.name.replace(/\.[^/.]+$/, "");
      setTrackTitle(nameWithoutExt);
    }
  };

  const handleCoverImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    
    const file = e.target.files[0];
    const validationError = validateImageFile(file);
    
    if (validationError) {
      toast.error(validationError);
      return;
    }

    setCoverImage(file);
  };

  // Auto-advance to details step when audio file is selected
  useEffect(() => {
    if (audioFile && step === "INITIAL") {
      setStep("DETAILS");
    }
  }, [audioFile, step]);

  // Upload handler with progress tracking
  const handleUpload = async () => {
    if (!audioFile) {
      toast.error("No audio file selected");
      return;
    }

    if (!trackTitle.trim() || !artist.trim()) {
      toast.error("Please enter both artist name and track title");
      return;
    }

    if (trackTitle.length > config.upload.maxTitleLength) {
      toast.error(`Title must be less than ${config.upload.maxTitleLength} characters`);
      return;
    }

    if (artist.length > config.upload.maxArtistLength) {
      toast.error(`Artist name must be less than ${config.upload.maxArtistLength} characters`);
      return;
    }

    setStep("UPLOADING");

    try {
      // Simulate progress updates
      setUploadProgress({ step: "Preparing", percentage: 10, message: "Preparing files..." });
      
      await new Promise(resolve => setTimeout(resolve, 500));
      setUploadProgress({ step: "Analyzing", percentage: 30, message: "Analyzing audio..." });
      
      await new Promise(resolve => setTimeout(resolve, 500));
      setUploadProgress({ step: "Uploading", percentage: 60, message: "Uploading to cloud..." });

      const result = await executeUpload(() => 
        apiClient.uploadAudio(audioFile, trackTitle.trim(), artist.trim(), coverImage || undefined)
      );

      if (result) {
        setUploadProgress({ step: "Complete", percentage: 100, message: "Upload successful!" });
        setStep("SUCCESS");
        
        toast.success(`Successfully uploaded "${result.title}"!`, {
          description: `By ${result.artist} - ID: ${result.id}`,
        });

        // Reset form after delay
        setTimeout(() => {
          resetForm();
          router.push("/dashboard");
        }, 2000);
      }

    } catch (error) {
      const appError = handleError(error, 'upload');
      showErrorToast(appError, 'Upload failed. Please try again.');
      setStep("DETAILS");
      setUploadProgress({ step: "", percentage: 0, message: "" });
    }
  };

  const resetForm = () => {
    setAudioFile(null);
    setCoverImage(null);
    setArtist("");
    setTrackTitle("");
    setStep("INITIAL");
    setUploadProgress({ step: "", percentage: 0, message: "" });
    
    // Reset file inputs
    if (audioInputRef.current) audioInputRef.current.value = "";
    if (coverImageRef.current) coverImageRef.current.value = "";
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <ProtectedRoute>
      <div className="min-h-screen w-full flex flex-col bg-gray-50 text-gray-800">
      {/* Step 1: File Selection */}
      {step === "INITIAL" && (
        <div className="flex-1 flex flex-col items-center justify-center px-4 py-10">
          <h2 className="text-2xl font-bold mb-3">Upload your audio file</h2>
          <p className="text-sm text-gray-600 mb-8">
            Select an audio file to upload and analyze ({config.upload.allowedAudioFormats.join(', ')})
          </p>

          {/* Drag & Drop area */}
          <div
            className="w-full max-w-xl border-2 border-dashed border-gray-400 rounded-lg p-10 flex flex-col items-center justify-center cursor-pointer hover:bg-gray-100 transition"
            onClick={() => audioInputRef.current?.click()}
            onDragOver={(e) => {
              e.preventDefault();
              e.currentTarget.classList.add('border-blue-400', 'bg-blue-50');
            }}
            onDragLeave={(e) => {
              e.currentTarget.classList.remove('border-blue-400', 'bg-blue-50');
            }}
            onDrop={(e) => {
              e.preventDefault();
              e.currentTarget.classList.remove('border-blue-400', 'bg-blue-50');
              const files = e.dataTransfer.files;
              if (files.length > 0) {
                const file = files[0];
                const validationError = validateAudioFile(file);
                if (validationError) {
                  toast.error(validationError);
                  return;
                }
                setAudioFile(file);
              }
            }}
          >
            <Upload className="w-12 h-12 text-gray-400 mb-4" />
            <p className="text-sm text-gray-600 mb-2">Drag & drop to get started</p>
            <p className="text-xs text-gray-500 mb-4">
              Max size: {config.upload.maxFileSize / (1024 * 1024)}MB
            </p>
            <Button variant="outline" className="border-gray-400 text-gray-700 hover:bg-gray-200">
              Choose file
            </Button>
          </div>

          <input
            type="file"
            ref={audioInputRef}
            className="hidden"
            accept={config.upload.allowedAudioFormats.join(',')}
            onChange={handleAudioChange}
          />
        </div>
      )}

      {/* Step 2: Track Details */}
      {step === "DETAILS" && audioFile && (
        <div className="flex-1 flex flex-col py-10 px-4 md:px-10 max-w-4xl mx-auto">
          <div className="mb-6 flex items-center justify-between">
            <div className="flex flex-col">
              <div className="text-sm font-medium text-gray-700 mb-1">{audioFile.name}</div>
              <div className="text-xs text-gray-500">
                {formatFileSize(audioFile.size)} • {audioFile.type}
              </div>
            </div>
            <Button 
              variant="outline" 
              size="sm"
              onClick={() => {
                setAudioFile(null);
                setStep("INITIAL");
              }}
            >
              Change file
            </Button>
          </div>

          <div className="flex flex-col md:flex-row md:space-x-8">
            {/* Cover Image Upload */}
            <div className="md:w-1/3 bg-gray-100 border-2 border-dashed border-gray-300 rounded-lg flex items-center justify-center p-4 relative aspect-square">
              {coverImage ? (
                <div className="relative w-full h-full">
                  <img
                    src={URL.createObjectURL(coverImage)}
                    alt="Cover"
                    className="object-cover w-full h-full rounded-md"
                  />
                  <Button
                    variant="destructive"
                    size="sm"
                    className="absolute top-2 right-2"
                    onClick={() => setCoverImage(null)}
                  >
                    Remove
                  </Button>
                </div>
              ) : (
                <div
                  className="text-center cursor-pointer flex flex-col items-center justify-center w-full h-full"
                  onClick={() => coverImageRef.current?.click()}
                >
                  <div className="w-16 h-16 bg-gray-200 rounded-md flex items-center justify-center mb-2">
                    <ImageIcon className="w-8 h-8 text-gray-500" />
                  </div>
                  <p className="text-sm text-gray-600">Add cover image</p>
                  <p className="text-xs text-gray-500 mt-1">Optional • Max 10MB</p>
                </div>
              )}

              <input
                type="file"
                accept={config.upload.allowedImageFormats.join(',')}
                ref={coverImageRef}
                className="hidden"
                onChange={handleCoverImageChange}
              />
            </div>

            {/* Track Information */}
            <div className="md:w-2/3 mt-6 md:mt-0 flex flex-col space-y-5">
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Artist *
                </label>
                <input
                  type="text"
                  value={artist}
                  onChange={(e) => setArtist(e.target.value)}
                  placeholder="Enter artist name"
                  maxLength={config.upload.maxArtistLength}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-400"
                  required
                />
                <div className="text-xs text-gray-500 mt-1">
                  {artist.length}/{config.upload.maxArtistLength} characters
                </div>
              </div>
              
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Track Title *
                </label>
                <input
                  type="text"
                  value={trackTitle}
                  onChange={(e) => setTrackTitle(e.target.value)}
                  placeholder="Enter track title"
                  maxLength={config.upload.maxTitleLength}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-400"
                  required
                />
                <div className="text-xs text-gray-500 mt-1">
                  {trackTitle.length}/{config.upload.maxTitleLength} characters
                </div>
              </div>

              <div className="bg-blue-50 border border-blue-200 rounded-md p-4">
                <h4 className="text-sm font-medium text-blue-800 mb-2">What happens next?</h4>
                <ul className="text-xs text-blue-700 space-y-1">
                  <li>• Your audio will be analyzed for musical features (BPM, key, etc.)</li>
                  <li>• Files will be securely stored in cloud storage</li>
                  <li>• You&apos;ll be able to play and share your track</li>
                </ul>
              </div>
            </div>
          </div>

          {/* Upload Button */}
          <div className="flex justify-end mt-8 space-x-3">
            <Button
              variant="outline"
              onClick={() => {
                setStep("INITIAL");
                setAudioFile(null);
              }}
              disabled={isUploading}
            >
              Back
            </Button>
            <Button
              onClick={handleUpload}
              disabled={isUploading || !trackTitle.trim() || !artist.trim()}
              className="bg-blue-600 hover:bg-blue-700 text-white"
            >
              {isUploading ? "Uploading..." : "Upload Track"}
            </Button>
          </div>
        </div>
      )}

      {/* Step 3: Upload Progress */}
      {step === "UPLOADING" && (
        <div className="flex-1 flex flex-col items-center justify-center px-4 py-10">
          <div className="w-full max-w-md">
            <div className="text-center mb-8">
              <Loader2 className="w-16 h-16 text-blue-600 animate-spin mx-auto mb-4" />
              <h2 className="text-2xl font-bold mb-2">Uploading your track</h2>
              <p className="text-gray-600">{uploadProgress.message}</p>
            </div>

            {/* Progress Bar */}
            <div className="w-full bg-gray-200 rounded-full h-3 mb-4">
              <div
                className="bg-blue-600 h-3 rounded-full transition-all duration-300"
                style={{ width: `${uploadProgress.percentage}%` }}
              />
            </div>

            <div className="text-center">
              <span className="text-sm text-gray-600">
                {uploadProgress.percentage}% complete
              </span>
            </div>

            {/* Steps indicator */}
            <div className="flex justify-center space-x-4 mt-8 text-xs">
              <div className={`flex items-center ${uploadProgress.percentage >= 10 ? 'text-blue-600' : 'text-gray-400'}`}>
                <CheckCircle className="w-4 h-4 mr-1" />
                Preparing
              </div>
              <div className={`flex items-center ${uploadProgress.percentage >= 30 ? 'text-blue-600' : 'text-gray-400'}`}>
                <CheckCircle className="w-4 h-4 mr-1" />
                Analyzing
              </div>
              <div className={`flex items-center ${uploadProgress.percentage >= 60 ? 'text-blue-600' : 'text-gray-400'}`}>
                <CheckCircle className="w-4 h-4 mr-1" />
                Uploading
              </div>
              <div className={`flex items-center ${uploadProgress.percentage === 100 ? 'text-green-600' : 'text-gray-400'}`}>
                <CheckCircle className="w-4 h-4 mr-1" />
                Complete
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Step 4: Success */}
      {step === "SUCCESS" && (
        <div className="flex-1 flex flex-col items-center justify-center px-4 py-10">
          <CheckCircle className="w-16 h-16 text-green-600 mb-4" />
          <h2 className="text-2xl font-bold mb-2 text-green-800">Upload Successful!</h2>
          <p className="text-gray-600 mb-6 text-center">
            Your track has been uploaded and analyzed successfully.
            <br />
            Redirecting to your library...
          </p>
          
          <div className="flex space-x-3">
            <Button
              variant="outline"
              onClick={resetForm}
            >
              Upload Another
            </Button>
            <Button
              onClick={() => router.push("/dashboard")}
              className="bg-green-600 hover:bg-green-700 text-white"
            >
              Go to Library
            </Button>
          </div>
        </div>
      )}

      {/* Error Display */}
      {uploadError && (
        <div className="fixed bottom-4 right-4 bg-red-50 border border-red-200 rounded-md p-4 max-w-sm">
          <div className="flex items-start">
            <AlertCircle className="w-5 h-5 text-red-600 mr-2 flex-shrink-0 mt-0.5" />
            <div>
              <h4 className="text-sm font-medium text-red-800">Upload Failed</h4>
              <p className="text-xs text-red-700 mt-1">{uploadError}</p>
            </div>
          </div>
        </div>
      )}
    </div>
    </ProtectedRoute>
  );
}
