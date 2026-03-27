"use client";

import { useRouter } from "next/navigation";
import { useCallback, useState } from "react";
import { DropZone } from "@/features/upload/components/DropZone";
import { UploadProgress } from "@/features/upload/components/UploadProgress";
import { ChatPicker, type ChatInfo } from "@/features/upload/components/ChatPicker";
import { TripForm, type TripFormData } from "@/features/upload/components/TripForm";
import { validateZipFile } from "@/features/upload/validators/zipValidator";
import { apiClient } from "@/lib/apiClient";
import { InstagramIcon } from "@/shared/components/InstagramIcon";
import type { CreateJobResponse } from "@/shared/types/jobs";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Step = "upload" | "uploading" | "pick_chat" | "focus" | "starting_job" | "error";

export default function HomePage() {
  const router = useRouter();
  const [step, setStep] = useState<Step>("upload");
  const [error, setError] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [fileUrl, setFileUrl] = useState<string | null>(null);
  const [chats, setChats] = useState<readonly ChatInfo[]>([]);
  const [selectedChatDir, setSelectedChatDir] = useState<string | null>(null);
  const [selectedChatTitle, setSelectedChatTitle] = useState<string>("");

  const reset = useCallback(() => {
    setStep("upload");
    setError(null);
    setFile(null);
    setFileUrl(null);
    setChats([]);
    setSelectedChatDir(null);
    setSelectedChatTitle("");
  }, []);

  const handleFileSelected = useCallback(async (selectedFile: File) => {
    setFile(selectedFile);

    const validation = validateZipFile(selectedFile);
    if (!validation.valid) {
      setStep("error");
      setError(validation.error);
      return;
    }

    setStep("uploading");

    try {
      const formData = new FormData();
      formData.append("file", selectedFile);

      const uploadResponse = await fetch(`${API_URL}/api/upload`, {
        method: "POST",
        body: formData,
      });

      if (!uploadResponse.ok) {
        throw new Error("Failed to upload file");
      }

      const { file_url } = (await uploadResponse.json()) as { file_url: string };
      setFileUrl(file_url);

      const chatList = await apiClient.get<ChatInfo[]>(
        `/chats?file_url=${encodeURIComponent(file_url)}`,
      );

      if (chatList.length === 0) {
        setStep("error");
        setError("No group chats found in this Instagram export. Make sure you exported Messages in JSON format.");
        return;
      }

      if (chatList.length === 1) {
        setSelectedChatDir(chatList[0].chat_dir);
        setSelectedChatTitle(chatList[0].title);
        setStep("focus");
        return;
      }

      setChats(chatList);
      setStep("pick_chat");
    } catch (err) {
      setStep("error");
      setError(err instanceof Error ? err.message : "Upload failed");
    }
  }, []);

  const startJob = useCallback(
    async (url: string, chatDir: string, tripData: TripFormData) => {
      setStep("starting_job");
      try {
        const job = await apiClient.post<CreateJobResponse>("/jobs", {
          file_url: url,
          chat_dir: chatDir,
          trip_details: tripData,
        });
        router.push(`/processing/${job.job_id}`);
      } catch (err) {
        setStep("error");
        setError(err instanceof Error ? err.message : "Failed to start processing");
      }
    },
    [router],
  );

  const handleChatSelect = useCallback(
    (chatDir: string) => {
      const chat = chats.find((c) => c.chat_dir === chatDir);
      setSelectedChatDir(chatDir);
      setSelectedChatTitle(chat?.title ?? "Selected chat");
      setStep("focus");
    },
    [chats],
  );

  const handleTripSubmit = useCallback(
    (tripData: TripFormData) => {
      if (fileUrl && selectedChatDir) {
        startJob(fileUrl, selectedChatDir, tripData);
      }
    },
    [fileUrl, selectedChatDir, startJob],
  );

  return (
    <main className="flex-1 flex flex-col items-center justify-center px-4 py-16">
      {/* Hero */}
      <div className="w-full max-w-2xl text-center mb-12">
        <div className="flex items-center justify-center gap-3 mb-5">
          <InstagramIcon size={40} />
          <h1 className="text-5xl font-bold tracking-tight text-slate-900">
            GroupFind
          </h1>
        </div>
        <p className="text-xl text-slate-600 leading-relaxed max-w-lg mx-auto">
          Turn your Instagram group chat into a
          <span className="font-semibold text-slate-800"> dream trip plan</span> with your best friends.
        </p>
        <p className="text-base text-slate-500 mt-3 max-w-md mx-auto">
          Every restaurant, bar, and spot you've shared &mdash; pulled from reels and messages,
          verified on Reddit, pinned on a map, and ready for your calendar.
        </p>
      </div>

      {/* Main content area */}
      <div className="w-full max-w-2xl">
        {step === "upload" && (
          <DropZone onFileSelected={handleFileSelected} />
        )}

        {step === "uploading" && (
          <UploadProgress
            status="uploading"
            fileName={file?.name ?? null}
            error={null}
            onRetry={reset}
          />
        )}

        {step === "pick_chat" && (
          <ChatPicker
            chats={chats}
            onSelect={handleChatSelect}
          />
        )}

        {step === "focus" && (
          <TripForm
            chatTitle={selectedChatTitle}
            onSubmit={handleTripSubmit}
            loading={false}
          />
        )}

        {step === "starting_job" && (
          <UploadProgress
            status="creating_job"
            fileName={file?.name ?? null}
            error={null}
            onRetry={reset}
          />
        )}

        {step === "error" && (
          <>
            <DropZone onFileSelected={handleFileSelected} />
            <div className="mt-4">
              <UploadProgress
                status="error"
                fileName={file?.name ?? null}
                error={error}
                onRetry={reset}
              />
            </div>
          </>
        )}
      </div>

      {/* How it works */}
      {step === "upload" && (
        <div className="mt-20 text-center w-full max-w-3xl">
          <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-8">
            How it works
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-10">
            {[
              {
                icon: (
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
                  </svg>
                ),
                title: "Export",
                desc: "Download your Instagram data as JSON",
              },
              {
                icon: <InstagramIcon size={24} />,
                title: "Upload",
                desc: "Drop the ZIP and pick your group chat",
              },
              {
                icon: (
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z" />
                  </svg>
                ),
                title: "Discover",
                desc: "AI finds every venue, Reddit verifies it",
              },
              {
                icon: (
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15 10.5a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1115 0z" />
                  </svg>
                ),
                title: "Plan",
                desc: "Pin on a map, add to your calendar",
              },
            ].map((item, i) => (
              <div key={i} className="flex flex-col items-center">
                <div className="w-12 h-12 rounded-2xl bg-white border border-slate-200 shadow-sm flex items-center justify-center text-slate-600 mb-4">
                  {item.icon}
                </div>
                <h3 className="font-semibold text-slate-800 text-sm">{item.title}</h3>
                <p className="text-sm text-slate-500 mt-1.5 leading-relaxed">{item.desc}</p>
              </div>
            ))}
          </div>

          {/* Export guide */}
          <div className="mt-16 max-w-xl mx-auto">
            <div className="p-6 bg-white rounded-2xl border border-slate-200 shadow-sm">
              <div className="flex items-center gap-3 mb-4">
                <InstagramIcon size={22} />
                <span className="text-sm font-semibold text-slate-800">How to export your Instagram data</span>
              </div>
              <ol className="space-y-3 text-sm text-slate-600 text-left">
                <li className="flex gap-3">
                  <span className="flex-shrink-0 w-6 h-6 rounded-full bg-slate-100 text-slate-500 text-xs font-bold flex items-center justify-center">1</span>
                  <span>Open Instagram &rarr; <strong className="text-slate-800">Settings and activity</strong> &rarr; <strong className="text-slate-800">Your activity</strong> &rarr; <strong className="text-slate-800">Download your information</strong></span>
                </li>
                <li className="flex gap-3">
                  <span className="flex-shrink-0 w-6 h-6 rounded-full bg-slate-100 text-slate-500 text-xs font-bold flex items-center justify-center">2</span>
                  <span>Tap <strong className="text-slate-800">Download or transfer information</strong> &rarr; select <strong className="text-slate-800">Some of your information</strong></span>
                </li>
                <li className="flex gap-3">
                  <span className="flex-shrink-0 w-6 h-6 rounded-full bg-slate-100 text-slate-500 text-xs font-bold flex items-center justify-center">3</span>
                  <span>Check only <strong className="text-slate-800">Messages</strong> &mdash; you don&apos;t need anything else</span>
                </li>
                <li className="flex gap-3">
                  <span className="flex-shrink-0 w-6 h-6 rounded-full bg-slate-100 text-slate-500 text-xs font-bold flex items-center justify-center">4</span>
                  <span>Tap <strong className="text-slate-800">Download to device</strong></span>
                </li>
                <li className="flex gap-3">
                  <span className="flex-shrink-0 w-6 h-6 rounded-full bg-slate-100 text-slate-500 text-xs font-bold flex items-center justify-center">5</span>
                  <div>
                    <span>Set these options:</span>
                    <div className="mt-2 grid grid-cols-2 gap-2">
                      <div className="px-3 py-2 bg-slate-50 rounded-lg">
                        <p className="text-xs text-slate-400">Date range</p>
                        <p className="font-medium text-slate-700">All time</p>
                      </div>
                      <div className="px-3 py-2 bg-slate-50 rounded-lg">
                        <p className="text-xs text-slate-400">Format</p>
                        <p className="font-medium text-slate-700">JSON</p>
                      </div>
                      <div className="px-3 py-2 bg-slate-50 rounded-lg">
                        <p className="text-xs text-slate-400">Media quality</p>
                        <p className="font-medium text-slate-700">Low</p>
                      </div>
                    </div>
                  </div>
                </li>
                <li className="flex gap-3">
                  <span className="flex-shrink-0 w-6 h-6 rounded-full bg-slate-100 text-slate-500 text-xs font-bold flex items-center justify-center">6</span>
                  <span>Tap <strong className="text-slate-800">Create files</strong> &mdash; Instagram will notify you when it&apos;s ready (usually a few minutes)</span>
                </li>
              </ol>
              <div className="mt-4 px-3 py-2 bg-amber-50 border border-amber-200 rounded-lg">
                <p className="text-xs text-amber-700">
                  <strong>Important:</strong> The format must be <strong>JSON</strong>, not HTML. Low quality is fine &mdash; we only read text and links, not media files.
                </p>
              </div>
            </div>
          </div>

          {/* Social proof / use case */}
          <div className="mt-8 p-6 bg-white rounded-2xl border border-slate-200 shadow-sm max-w-xl mx-auto">
            <div className="flex items-center gap-3 mb-3">
              <InstagramIcon size={20} />
              <span className="text-sm font-medium text-slate-700">Built for group chats</span>
            </div>
            <p className="text-sm text-slate-500 leading-relaxed text-left">
              You and your friends send each other reels of restaurants, bars, and places to visit all the time.
              GroupFind turns that chaotic group chat into an organized trip plan &mdash;
              every spot verified, mapped, and ready to go. Stop scrolling back through months of messages.
              Start planning the trip.
            </p>
          </div>
        </div>
      )}
    </main>
  );
}
