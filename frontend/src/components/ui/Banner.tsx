import React from 'react';

interface BannerProps {
  title: string;
  content: string;
  linkText?: string;
  onLinkClick?: () => void;
  onClose: () => void;
  variant?: 'default' | 'info';
}

export const Banner: React.FC<BannerProps> = ({
  title,
  content,
  linkText,
  onLinkClick,
  onClose,
  variant = 'default',
}) => {
  const styles = {
    default: 'bg-white border-line',
    info: 'bg-blue-50 border-blue-100',
  };

  const titleStyles = {
    default: 'bg-gradient-to-r from-indigo-700 to-indigo-600 text-white',
    info: 'bg-blue-600 text-white',
  };

  return (
    <div className={`banner min-h-[50px] border shadow-sm flex items-center mb-4 ${styles[variant]}`}>
      <div className={`h-full min-h-12 font-semibold px-4 flex items-center ${titleStyles[variant]}`}>
        {title}
      </div>
      <div className="px-4 text-slate-600 flex-1">
        {content}
      </div>
      {linkText && (
        <a
          href="#"
          onClick={(e) => {
            e.preventDefault();
            onLinkClick?.();
          }}
          className="text-blue mr-5 hover:underline"
        >
          {linkText} →
        </a>
      )}
      <button
        onClick={onClose}
        className="px-4 text-xl text-slate-500 hover:text-black"
      >
        ×
      </button>
    </div>
  );
};
