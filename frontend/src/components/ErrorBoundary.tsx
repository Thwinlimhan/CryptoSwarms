import { Component, type ReactNode } from 'react';

interface Props { children: ReactNode; }
interface State { hasError: boolean; error?: Error; }

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="border-box" style={{ padding: '2rem', textAlign: 'center' }}>
          <h2>SYSTEM_ERROR</h2>
          <p className="text-muted">{this.state.error?.message}</p>
          <button onClick={() => window.location.reload()}>RELOAD</button>
        </div>
      );
    }
    return this.props.children;
  }
}
