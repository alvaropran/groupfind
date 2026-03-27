"use client";

interface ChatInfo {
  readonly chat_dir: string;
  readonly title: string;
  readonly participant_count: number;
  readonly participants: readonly string[];
  readonly message_count: number;
}

interface ChatPickerProps {
  readonly chats: readonly ChatInfo[];
  readonly onSelect: (chatDir: string) => void;
  readonly loading?: boolean;
}

export function ChatPicker({ chats, onSelect, loading = false }: ChatPickerProps) {
  if (chats.length === 0) {
    return (
      <div className="text-center py-8">
        <p className="text-gray-500">No group chats found in this export.</p>
      </div>
    );
  }

  return (
    <div className="w-full max-w-2xl mx-auto">
      <h2 className="text-xl font-semibold text-gray-900 mb-2">
        Select a group chat
      </h2>
      <p className="text-sm text-gray-500 mb-6">
        We found {chats.length} chat{chats.length > 1 ? "s" : ""} in your export.
        Pick the one you want to analyze.
      </p>

      <div className="space-y-3">
        {chats.map((chat) => (
          <button
            key={chat.chat_dir}
            onClick={() => onSelect(chat.chat_dir)}
            disabled={loading}
            className={`
              w-full text-left p-4 bg-white border rounded-xl shadow-sm
              transition-all duration-150
              ${loading ? "opacity-50 cursor-not-allowed" : "hover:border-blue-400 hover:shadow-md cursor-pointer"}
            `}
          >
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-medium text-gray-900">{chat.title}</h3>
                <p className="text-sm text-gray-500 mt-0.5">
                  {chat.participant_count} participants &middot;{" "}
                  {chat.message_count.toLocaleString()} messages
                </p>
                <p className="text-xs text-gray-400 mt-1 truncate max-w-md">
                  {chat.participants.join(", ")}
                </p>
              </div>
              <svg
                className="w-5 h-5 text-gray-400 flex-shrink-0"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 5l7 7-7 7"
                />
              </svg>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

export type { ChatInfo };
