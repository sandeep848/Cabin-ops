import { Component } from 'react';

/** Optional graphics cannot prevent access to core cabin services. */
export default class OptionalView extends Component {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() {
    return this.state.failed ? <p role="status">3D view is unavailable. Use the service buttons or seat map below.</p> : this.props.children;
  }
}
