import React from 'react';

interface BadgeProps {
  children: React.ReactNode;
  variant: 'recovered' | 'pending' | 'unresolved' | 'stopped' | 'info' | 'ai' | 'update';
}

const variantStyles = {
  recovered: 'bg-[#ecfdf3] text-[#15803d]',
  pending: 'bg-[#fff7ed] text-[#c2410c]',
  unresolved: 'bg-[#fef2f2] text-[#dc2626]',
  stopped: 'bg-[#f3f4f6] text-[#4b5563]',
  info: 'bg-blue-100 text-blue-700',
  ai: 'bg-[#ddd6fe] text-indigo-700',
  update: 'bg-[#d1fae5] text-emerald-700',
};

export const Badge: React.FC<BadgeProps> = ({ children, variant }) => {
  return (
    <span className={`px-2 py-0.5 rounded-full text-[11px] font-medium inline-flex items-center ${variantStyles[variant]}`}>
      {children}
    </span>
  );
};
