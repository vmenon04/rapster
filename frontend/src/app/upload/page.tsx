"use client";

import { useState, useRef } from "react";
import { Upload, X, Image as ImageIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { toast } from "sonner"; // ✅ Notifications
import { useRouter } from "next/navigation";

export default function UploadPage() {
  const [files, setFiles] = useState<{ audio: File; image?: File | null }[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const audioInputRef = useRef<HTMLInputElement | null>(null);
  const imageInputRefs = useRef<{ [key: number]: HTMLInputElement | null }>({});

  const router = useRouter();

  // ✅ Handle audio selection
  const handleAudioChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files) {
      const newAudioFiles = Array.from(event.target.files).map((file) => ({
        audio: file,
        image: null, // ✅ Ensure image starts as null
      }));

      setFiles((prevFiles) => [
        ...prevFiles.filter((existing) =>
          newAudioFiles.every((newFile) => newFile.audio.name !== existing.audio.name)
        ),
        ...newAudioFiles,
      ]);
    }
  };

  // ✅ Handle image selection
  const handleImageChange = (event: React.ChangeEvent<HTMLInputElement>, index: number) => {
    if (event.target.files?.[0]) {
      setFiles((prevFiles) =>
        prevFiles.map((file, i) =>
          i === index ? { ...file, image: event.target.files![0] } : file
        )
      );
    }
  };

  // ✅ Remove an audio file and its associated image
  const removeFile = (index: number) => {
    setFiles((prevFiles) => prevFiles.filter((_, i) => i !== index));
  };

  // ✅ Remove an image and reset input
  const removeImage = (index: number) => {
    setFiles((prevFiles) =>
      prevFiles.map((file, i) => (i === index ? { ...file, image: null } : file))
    );

    if (imageInputRefs.current[index]) {
      imageInputRefs.current[index]!.value = "";
    }
  };

  // ✅ Upload function
  const handleUpload = async () => {

    if (files.length === 0) {
      toast.warning("No files selected", { description: "Please select audio files to upload." });
      return;
    }

    setIsUploading(true);

    for (const fileObj of files) {
      const formData = new FormData();
      formData.append("file", fileObj.audio);

      if (fileObj.image) {
        formData.append("image", fileObj.image);
      }

      try {
        const response = await fetch("http://127.0.0.1:8000/audio/upload/", {
          method: "POST",
          body: formData,
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || "Upload failed");
        }

        toast.success(`Uploaded ${fileObj.audio.name}!`);
      } catch (error) {
        console.error("❌ Upload Error:", error);
        const errorMessage = error instanceof Error ? error.message : "Unknown error";
        toast.error("Upload failed", { description: errorMessage });
      }
    }

    setFiles([]); // ✅ Clears all files after upload
    setIsUploading(false);
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-white p-6">
      <Card className="w-full max-w-lg p-6 border border-gray-300 shadow-md">
        {/* ✅ Audio Upload Box */}
        <div
          className="border-2 border-dashed border-gray-400 p-10 text-center cursor-pointer hover:bg-gray-100 transition rounded-lg"
          onClick={() => audioInputRef.current?.click()}
        >
          <Upload className="w-12 h-12 text-gray-500 mx-auto" />
          <p className="mt-2 text-gray-600">
            Drag & Drop audio files or <span className="text-blue-600">Click to Select</span>
          </p>
        </div>

        {/* ✅ Hidden File Input */}
        <input
          type="file"
          ref={audioInputRef}
          multiple
          onChange={handleAudioChange}
          className="hidden"
          accept="audio/*"
        />

        {/* ✅ File List */}
        {files.length > 0 && (
          <div className="mt-4 space-y-4">
            {files.map(({ audio, image }, index) => (
              <div key={index} className="p-3 bg-gray-100 rounded-lg">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <span className="text-gray-700 truncate">{audio.name}</span>
                    <span className="text-xs text-gray-500">
                      ({(audio.size / 1024 / 1024).toFixed(2)} MB)
                    </span>
                  </div>
                  <button onClick={() => removeFile(index)} className="text-red-500 hover:text-red-700">
                    <X className="w-5 h-5" />
                  </button>
                </div>

                {/* ✅ Image Upload Section for this Audio File */}
                <div
                  className="mt-2 border border-dashed border-gray-400 p-3 text-center cursor-pointer hover:bg-gray-200 transition rounded-md"
                  onClick={() => document.getElementById(`imageInput-${index}`)?.click()}
                >
                  <ImageIcon className="w-6 h-6 text-gray-500 mx-auto" />
                  <p className="text-sm text-gray-600">
                    {image ? "Change Image" : "Attach Cover Image"}
                  </p>
                </div>

                {/* ✅ Hidden Image Input */}
                <input
                  type="file"
                  id={`imageInput-${index}`}
                  ref={(el) => {
                    imageInputRefs.current[index] = el;
                  }}
                  onChange={(e) => handleImageChange(e, index)}
                  className="hidden"
                  accept="image/*"
                />

                {/* ✅ Display Selected Image */}
                {image && (
                  <div className="mt-2 flex items-center gap-2">
                    <img
                      src={URL.createObjectURL(image)}
                      alt="Preview"
                      className="w-16 h-16 rounded-md object-cover border border-gray-300"
                    />
                    <button
                      onClick={() => removeImage(index)}
                      className="text-red-500 hover:text-red-700"
                    >
                      <X className="w-5 h-5" />
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* ✅ Upload Button */}
        <Button onClick={handleUpload} disabled={isUploading} className="mt-4 w-full">
          {isUploading ? "Uploading..." : "Upload"}
        </Button>
      </Card>
    </div>
  );
}
