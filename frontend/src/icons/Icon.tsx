import { memo } from 'react';
import { ICONS, AVATARS, TIERS } from './icons.mjs';
import styles from './Icon.module.css';

export type IconName = keyof typeof ICONS | string;

interface IconProps {
  name: IconName;
  size?: number;
  className?: string;
  title?: string;
  /** Accent fill colour for the duotone shapes (defaults to the highlighter). */
  accent?: string;
}

/** Custom ZENITH duotone icon. Decorative unless `title` is provided. */
export const Icon = memo(function Icon({ name, size = 22, className, title, accent }: IconProps) {
  const markup = ICONS[name];
  if (!markup) return null;
  return (
    <svg
      className={`${styles.icon} ${className ?? ''}`}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      style={accent ? ({ ['--icon-accent' as string]: accent } as React.CSSProperties) : undefined}
      role={title ? 'img' : undefined}
      aria-label={title}
      aria-hidden={title ? undefined : true}
      focusable="false"
      dangerouslySetInnerHTML={{ __html: markup }}
    />
  );
});

export const AVATAR_IDS = Object.keys(AVATARS);

/** Custom character avatar. Falls back to the first avatar for unknown ids. */
export const Avatar = memo(function Avatar({
  id,
  size = 40,
  label,
  className,
}: {
  id?: string | null;
  size?: number;
  label?: string;
  className?: string;
}) {
  const [bg, art] = AVATARS[id ?? ''] ?? AVATARS[AVATAR_IDS[0]];
  return (
    <svg
      className={`${styles.avatar} ${className ?? ''}`}
      width={size}
      height={size}
      viewBox="0 0 48 48"
      role={label ? 'img' : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
    >
      <circle cx="24" cy="24" r="23" fill={bg} stroke="var(--ink)" strokeWidth="2" />
      <g clipPath="url(#zav)" dangerouslySetInnerHTML={{ __html: art }} />
    </svg>
  );
});

/** Shared clip path for avatars; render once near the app root. */
export function IconDefs() {
  return (
    <svg width="0" height="0" style={{ position: 'absolute' }} aria-hidden="true">
      <defs>
        <clipPath id="zav">
          <circle cx="24" cy="24" r="22" />
        </clipPath>
      </defs>
    </svg>
  );
}

export const TierBadge = memo(function TierBadge({
  tier,
  size = 56,
  active = true,
}: {
  tier: string;
  size?: number;
  active?: boolean;
}) {
  const t = TIERS.find((x) => x.id === tier) ?? TIERS[0];
  return (
    <span
      className={`${styles.tier} ${active ? styles.tierOn : ''}`}
      style={{ width: size, height: size, ['--tier' as string]: t.color } as React.CSSProperties}
      title={t.name}
    >
      <Icon name={t.icon} size={Math.round(size * 0.55)} accent={t.color} />
    </span>
  );
});
