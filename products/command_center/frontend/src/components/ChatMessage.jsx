import { Bot, User } from 'lucide-react';

export default function ChatMessage({ message }) {
  const isAssistant = message.role === 'assistant';

  return (
    <div className={`flex gap-2.5 animate-fade-in ${isAssistant ? '' : 'flex-row-reverse'}`}>
      <div className={`flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center ${
        isAssistant ? 'bg-blue-500/20 text-blue-400' : 'bg-white/10 text-gray-400'
      }`}>
        {isAssistant ? <Bot size={12} /> : <User size={12} />}
      </div>
      <div className={`max-w-[80%] text-sm leading-relaxed px-3 py-2 rounded-xl ${
        isAssistant
          ? 'bg-white/5 text-gray-300 rounded-tl-sm'
          : 'bg-blue-500/15 text-blue-100 rounded-tr-sm'
      }`}>
        <div className="whitespace-pre-wrap break-words">{message.content}</div>
      </div>
    </div>
  );
}
