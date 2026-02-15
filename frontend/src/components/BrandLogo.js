import React from "react";

function BrandLogo({ small = false }) {
  const cls = small ? "logo-orb footer-logo" : "logo-orb";

  return (
    <div className={cls} aria-label="FinPrint logo">
      <svg viewBox="0 0 28 28" className="logo-svg" aria-hidden="true">
        <circle className="brand-ring" cx="14" cy="14" r="10.2" />
        <path className="brand-f" d="M10 8.4h8.2M10 13.2h6M10 8.4v11.2" />
        <path className="brand-trend" d="M12.7 19.3l2.5-2.4 1.9 1.6 2.4-2.8" />
        <circle className="brand-dot" cx="19.4" cy="15.7" r="1.2" />
      </svg>
    </div>
  );
}

export default BrandLogo;
