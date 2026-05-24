import { Bot, Leaf, Send, Sparkles } from "lucide-react";

const prompts = ["What should I do after tomato early blight?", "Suggest fertilizer for mango flowering", "How does rain affect coconut leaf rot?", "Which products match my last diagnosis?"];

export default function AssistantPage() {
  return (
    <main className="pageStack assistantPage">
      <section className="pageHero compactHero"><div><span className="eyebrowText">AI Farming Assistant</span><h1>Ask practical farming questions.</h1><p>Conversation history, suggested questions, disease advice, fertilizer guidance, crop recommendations, and weather-aware support.</p></div></section>
      <section className="assistantLayout">
        <aside className="panel assistantSidebar"><h2>Suggested questions</h2>{prompts.map((prompt) => <button className="secondaryButton" key={prompt} type="button"><Sparkles size={16} /> {prompt}</button>)}</aside>
        <section className="panel chatPanel">
          <div className="chatMessages">
            <article className="assistantBubble"><Bot size={20} /><p>Hello. I can help with disease advice, crop care, fertilizer suggestions, weather actions, and marketplace recommendations.</p></article>
            <article className="userBubble"><Leaf size={20} /><p>Show my quick farming actions.</p></article>
            <article className="assistantBubble"><Bot size={20} /><p>Start with a disease scan, check weather risk, review history, then shop recommended inputs.</p></article>
          </div>
          <label className="chatInput"><input placeholder="Ask AgroMind AI..." /><button aria-label="Send message" type="button"><Send size={18} /></button></label>
        </section>
      </section>
    </main>
  );
}
