import React from 'react';

interface BadgeProps {
  children: React.ReactNode;
  variant: 'recovered' | 'pending' | 'unresolved' | 'stopped' | 'info' | 'ai' | 'update';
}

const variantStyles = {
  recovered: 'bg-emerald-500',
  pending: 'bg-amber-500',
  unresolved: 'bg-red-500',
  stopped: 'bg-gray-500',
  info: 'bg-blue-500',
  ai: 'bg-[var(--lav)] text-indigo-700',
  update: 'bg-[var(--mint)] text-emerald-700',
};

export const Badge: React.FC<BadgeProps> = ({ children, variant }) => {
  const isSpecial = ['ai', 'update'].includes(variant);

  return (
    <span className={`status-badge ${isSpecial ? variantStyles[variant] : variantStyles[variant]}`}>
      {children}
    </span>
  );
};
