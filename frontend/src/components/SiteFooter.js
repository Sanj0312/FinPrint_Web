import React from "react";
import BrandLogo from "./BrandLogo";

function SiteFooter() {
  const year = new Date().getFullYear();

  return (
    <footer className="site-footer">
      <div className="footer-brand">
        <BrandLogo small />
        <div>
          <strong>FinPrint by Fynx</strong>
          <p className="meta">Smart finance. Clear decisions. Better habits.</p>
        </div>
      </div>

      <div className="footer-socials">
        <a href="https://instagram.com" target="_blank" rel="noreferrer" aria-label="Instagram">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M7.8 2h8.4A5.8 5.8 0 0 1 22 7.8v8.4a5.8 5.8 0 0 1-5.8 5.8H7.8A5.8 5.8 0 0 1 2 16.2V7.8A5.8 5.8 0 0 1 7.8 2Zm0 1.8A4 4 0 0 0 3.8 7.8v8.4a4 4 0 0 0 4 4h8.4a4 4 0 0 0 4-4V7.8a4 4 0 0 0-4-4H7.8Zm8.9 1.5a1.3 1.3 0 1 1 0 2.6 1.3 1.3 0 0 1 0-2.6ZM12 7a5 5 0 1 1 0 10 5 5 0 0 1 0-10Zm0 1.8a3.2 3.2 0 1 0 0 6.4 3.2 3.2 0 0 0 0-6.4Z" />
          </svg>
        </a>
        <a href="https://x.com" target="_blank" rel="noreferrer" aria-label="X">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M18.9 3H22l-6.8 7.8L23 21h-6.3l-4.9-6.3L6.3 21H3.1l7.3-8.4L1 3h6.5l4.4 5.8L18.9 3Zm-1.1 16.1h1.7L6.6 4.8H4.8l13 14.3Z" />
          </svg>
        </a>
        <a href="https://linkedin.com" target="_blank" rel="noreferrer" aria-label="LinkedIn">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M6 8.5H2.7V21H6V8.5ZM4.3 3A2 2 0 1 0 4.3 7a2 2 0 0 0 0-4Zm17 9.7c0-3-1.6-4.4-3.9-4.4-1.8 0-2.6 1-3 1.7V8.5h-3.3V21h3.3v-6.2c0-1.6.3-3.2 2.3-3.2 1.9 0 2 1.8 2 3.3V21H22v-8.3h-.7Z" />
          </svg>
        </a>
        <a href="https://github.com" target="_blank" rel="noreferrer" aria-label="GitHub">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M12 2a10 10 0 0 0-3.2 19.5c.5.1.7-.2.7-.5v-1.7c-2.8.6-3.4-1.2-3.4-1.2-.4-1.1-1-1.4-1-1.4-.9-.6.1-.6.1-.6 1 .1 1.6 1 1.6 1 .9 1.5 2.4 1.1 3 .8.1-.7.4-1.1.6-1.4-2.3-.3-4.7-1.1-4.7-5a3.9 3.9 0 0 1 1-2.7 3.6 3.6 0 0 1 .1-2.7s.8-.3 2.8 1a9.6 9.6 0 0 1 5.1 0c2-1.3 2.8-1 2.8-1 .5 1.3.2 2.3.1 2.7a3.9 3.9 0 0 1 1 2.7c0 3.9-2.4 4.7-4.7 5 .4.3.7 1 .7 2v3c0 .3.2.6.7.5A10 10 0 0 0 12 2Z" />
          </svg>
        </a>
      </div>

      <div className="footer-actions">
        <button
          type="button"
          className="footer-link-btn"
          onClick={() => window.alert("Cookie preferences saved for this demo app.")}
        >
          Cookie Preferences
        </button>
        <span className="meta">End credits: Designed and built by Fynx.</span>
        <span className="meta">© {year} FinPrint by Fynx</span>
      </div>
    </footer>
  );
}

export default SiteFooter;
