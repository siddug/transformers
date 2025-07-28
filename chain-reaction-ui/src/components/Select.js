'use client';

import { useState, useRef, useEffect } from 'react';

export default function Select({ 
  value, 
  onChange, 
  options, 
  placeholder = "Select an option", 
  size = "medium", // small, medium
  className = "" 
}) {
  const [isOpen, setIsOpen] = useState(false);
  const selectRef = useRef(null);

  useEffect(() => {
    function handleClickOutside(event) {
      if (selectRef.current && !selectRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const selectedOption = options.find(opt => 
    (typeof opt === 'object' ? opt.value : opt) === value
  );

  const displayValue = selectedOption
    ? (typeof selectedOption === 'object' ? selectedOption.label : selectedOption)
    : placeholder;

  const sizeClasses = {
    small: "px-2 py-1 text-sm",
    medium: "px-3 py-1.25"
  };

  const iconSizes = {
    small: "w-4 h-4",
    medium: "w-5 h-5"
  };

  return (
    <div ref={selectRef} className={`relative ${className}`}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={`w-full ${sizeClasses[size]} text-left bg-white border border-gray-300 rounded hover:border-gray-400 focus:outline-none transition-colors cursor-pointer`}
      >
        <span className="block truncate">{displayValue}</span>
        <span className={`absolute inset-y-0 right-0 flex items-center ${size === 'small' ? 'pr-2' : 'pr-4'} pointer-events-none`}>
          <svg
            className={`${iconSizes[size]} text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </span>
      </button>

      {isOpen && (
        <div className="absolute z-10 w-full mt-1 bg-white border border-gray-200 rounded shadow-lg">
          <ul className="py-1 max-h-60 overflow-auto">
            {options.map((option, index) => {
              const optionValue = typeof option === 'object' ? option.value : option;
              const optionLabel = typeof option === 'object' ? option.label : option;
              const isSelected = optionValue === value;

              return (
                <li key={index}>
                  <button
                    type="button"
                    onClick={() => {
                      onChange({ value: optionValue, label: optionLabel });
                      setIsOpen(false);
                    }}
                    className={`w-full ${size === 'small' ? 'px-3 py-1.5 text-sm' : 'px-4 py-2'} text-left hover:bg-gray-100 transition-colors ${
                      isSelected ? 'bg-gray-50 font-medium' : ''
                    }`}
                  >
                    {optionLabel}
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}