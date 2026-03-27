"use client";

import { useCallback, useRef, useState } from "react";
import { InstagramIcon } from "@/shared/components/InstagramIcon";

interface DropZoneProps {
  readonly onFileSelected: (file: File) => void;
  readonly disabled?: boolean;
}

export function DropZone({ onFileSelected, disabled = false }: DropZoneProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      if (!disabled) setIsDragOver(true);
    },
    [disabled],
  );

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);
      if (disabled) return;

      const file = e.dataTransfer.files[0];
      if (file) onFileSelected(file);
    },
    [disabled, onFileSelected],
  );

  const handleClick = useCallback(() => {
    if (!disabled) inputRef.current?.click();
  }, [disabled]);

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) onFileSelected(file);
    },
    [onFileSelected],
  );

  return (
    <div
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      onClick={handleClick}
      className={`
        flex flex-col items-center justify-center
        w-full h-64 border-2 border-dashed rounded-2xl
        cursor-pointer transition-all duration-200
        ${isDragOver ? "border-violet-400 bg-violet-50" : "border-slate-300 bg-white hover:bg-slate-50 hover:border-slate-400"}
        ${disabled ? "opacity-50 cursor-not-allowed" : ""}
      `}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".zip"
        onChange={handleFileChange}
        className="hidden"
        disabled={disabled}
      />
      <InstagramIcon size={36} className="mb-4" />
      <p className="text-lg font-semibold text-slate-800">
        Drop your Instagram export here
      </p>
      <p className="text-sm text-slate-500 mt-1.5">
        or click to browse &middot; ZIP file &middot; max 500MB
      </p>
    </div>
  );
}
