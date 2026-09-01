import React from 'react';

interface ToggleProps {
  on: boolean;
  onChange: (value: boolean) => void;
  className?: string;
}

export const Toggle: React.FC<ToggleProps> = ({ on, onChange, className = '' }) => {
  return (
    <div
      className={`custom-toggle ${on ? 'on' : ''} ${className}`}
      onClick={() => onChange(!on)}
    >
      <i></i>
    </div>
  );
};
