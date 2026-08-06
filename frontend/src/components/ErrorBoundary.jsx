import { Component } from 'react';

export default class ErrorBoundary extends Component {
  state = { hasError: false, errorMsg: '' };

  static getDerivedStateFromError(error) {
    return { hasError: true, errorMsg: error?.message || 'Unknown error' };
  }

  componentDidCatch(error, info) {
    console.error('[ErrorBoundary]', error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'var(--bg-base)',
          color: 'var(--text-muted)',
          fontFamily: 'IBM Plex Mono',
          fontSize: 12,
          gap: 8,
        }}>
          <span>Map failed to load.</span>
          <button
            onClick={() => this.setState({ hasError: false })}
            style={{
              background: 'var(--bg-surface)',
              border: '1px solid var(--border)',
              color: 'var(--text-secondary)',
              padding: '4px 12px',
              cursor: 'pointer',
              fontSize: 11,
              fontFamily: 'IBM Plex Mono',
            }}
          >
            Retry
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
