import { ScanLine } from "lucide-react";

export default function FloatingActionButton() {
  return (
    <a aria-label="Start crop prediction" className="fab" href="/dashboard#predict">
      <ScanLine size={24} />
    </a>
  );
}
