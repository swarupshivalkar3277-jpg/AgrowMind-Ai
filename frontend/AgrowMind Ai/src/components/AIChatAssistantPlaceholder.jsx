import { Bot } from "lucide-react";

export default function AIChatAssistantPlaceholder() {
  return (
    <article className="chatPlaceholder">
      <Bot size={24} />
      <strong>AI farm assistant</strong>
      <p>Ask crop, irrigation, and marketplace questions from this workspace soon.</p>
    </article>
  );
}
