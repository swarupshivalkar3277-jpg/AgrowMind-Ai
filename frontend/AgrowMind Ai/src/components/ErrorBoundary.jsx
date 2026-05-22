import { Component } from "react";
import { AlertTriangle } from "lucide-react";

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  render() {
    if (this.state.hasError) {
      return (
        <main className="stateScreen">
          <AlertTriangle size={34} />
          <h1>Something needs attention</h1>
          <p>Refresh the page or return to the dashboard to continue.</p>
          <a className="primaryButton" href="/dashboard">Open Dashboard</a>
        </main>
      );
    }

    return this.props.children;
  }
}
