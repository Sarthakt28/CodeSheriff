import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'  // Tailwind + global styles

// Find the root DOM node declared in index.html and mount React into it.
// StrictMode runs components twice in dev to surface bugs early.
ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
