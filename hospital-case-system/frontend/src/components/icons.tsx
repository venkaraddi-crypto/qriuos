/* Single-stroke inline SVG icon set — no emoji, no icon fonts. */
type P = { size?: number; className?: string };

const base = (size: number, className?: string) => ({
  width: size,
  height: size,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.6,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
  className,
  "aria-hidden": true,
});

export const IconLeaf = ({ size = 20, className }: P) => (
  <svg {...base(size, className)}>
    <path d="M4 20c0-8 4-14 16-16-1 10-6 15-14 16" />
    <path d="M4 20c4-5 7-8 11-11" />
  </svg>
);
export const IconMic = ({ size = 20, className }: P) => (
  <svg {...base(size, className)}>
    <rect x="9" y="3" width="6" height="11" rx="3" />
    <path d="M5 11a7 7 0 0 0 14 0M12 18v3M9 21h6" />
  </svg>
);
export const IconAlert = ({ size = 20, className }: P) => (
  <svg {...base(size, className)}>
    <path d="M12 3 2 20h20L12 3zM12 10v4M12 17v.5" />
  </svg>
);
export const IconLogout = ({ size = 20, className }: P) => (
  <svg {...base(size, className)}>
    <path d="M10 4H5v16h5M14 8l4 4-4 4M18 12H9" />
  </svg>
);
export const IconQr = ({ size = 20, className }: P) => (
  <svg {...base(size, className)}>
    <rect x="3" y="3" width="7" height="7" /><rect x="14" y="3" width="7" height="7" /><rect x="3" y="14" width="7" height="7" />
    <path d="M14 14h3v3M21 14v7h-7M17 21v-2" />
  </svg>
);
export const IconUser = ({ size = 20, className }: P) => (
  <svg {...base(size, className)}>
    <circle cx="12" cy="8" r="4" /><path d="M4 21c0-4 4-6 8-6s8 2 8 6" />
  </svg>
);
export const IconCalendar = ({ size = 20, className }: P) => (
  <svg {...base(size, className)}>
    <rect x="3" y="5" width="18" height="16" rx="1" /><path d="M3 10h18M8 3v4M16 3v4" />
  </svg>
);
export const IconFile = ({ size = 20, className }: P) => (
  <svg {...base(size, className)}>
    <path d="M6 3h8l4 4v14H6zM14 3v4h4M9 12h6M9 16h6" />
  </svg>
);
export const IconBell = ({ size = 20, className }: P) => (
  <svg {...base(size, className)}>
    <path d="M6 16V11a6 6 0 0 1 12 0v5l2 2H4zM10 20a2 2 0 0 0 4 0" />
  </svg>
);
export const IconCheck = ({ size = 20, className }: P) => (
  <svg {...base(size, className)}><path d="M4 12l5 5L20 6" /></svg>
);
export const IconX = ({ size = 20, className }: P) => (
  <svg {...base(size, className)}><path d="M6 6l12 12M18 6 6 18" /></svg>
);
export const IconPlus = ({ size = 20, className }: P) => (
  <svg {...base(size, className)}><path d="M12 5v14M5 12h14" /></svg>
);
export const IconPrint = ({ size = 20, className }: P) => (
  <svg {...base(size, className)}>
    <path d="M7 8V3h10v5M5 8h14a2 2 0 0 1 2 2v7h-4v4H7v-4H3v-7a2 2 0 0 1 2-2zM7 14h10" />
  </svg>
);
export const IconLock = ({ size = 20, className }: P) => (
  <svg {...base(size, className)}>
    <rect x="5" y="11" width="14" height="10" rx="1" /><path d="M8 11V7a4 4 0 0 1 8 0v4" />
  </svg>
);
export const IconSpeaker = ({ size = 20, className }: P) => (
  <svg {...base(size, className)}>
    <path d="M4 10v4h4l5 4V6L8 10zM16 9a4 4 0 0 1 0 6M19 7a7 7 0 0 1 0 10" />
  </svg>
);
export const IconArrow = ({ size = 20, className }: P) => (
  <svg {...base(size, className)}><path d="M5 12h14M13 6l6 6-6 6" /></svg>
);
export const IconSun = ({ size = 20, className }: P) => (
  <svg {...base(size, className)}>
    <circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.5 1.5M17.5 17.5 19 19M5 19l1.5-1.5M17.5 6.5 19 5" />
  </svg>
);
export const IconMoon = ({ size = 20, className }: P) => (
  <svg {...base(size, className)}><path d="M20 15A8 8 0 0 1 9 4a8 8 0 1 0 11 11z" /></svg>
);
