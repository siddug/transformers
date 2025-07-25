'use client';

export default function Button({ 
  children, 
  onClick, 
  disabled = false, 
  loading = false,
  variant = 'primary', // primary, secondary, danger
  size = 'medium', // small, medium, large
  className = '',
  ...props 
}) {
  const baseStyles = 'font-medium transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2';
  
  const variantStyles = {
    primary: `
      bg-gray-900 text-white hover:bg-gray-800 
      disabled:bg-gray-300 disabled:text-gray-500
    `,
    secondary: `
      bg-white text-gray-900 border border-gray-300 hover:bg-gray-50
      disabled:bg-gray-100 disabled:text-gray-400 disabled:border-gray-200
    `,
    danger: `
      bg-white text-gray-900 border border-gray-300 hover:bg-gray-50 hover:border-red-300 hover:text-red-600
      disabled:bg-gray-100 disabled:text-gray-400 disabled:border-gray-200
    `
  };

  const sizeStyles = {
    small: 'px-3 py-1.5 text-sm rounded',
    medium: 'px-4 py-2 text-base rounded',
    large: 'px-6 py-3 text-lg rounded'
  };

  const isDisabled = disabled || loading;

  return (
    <button
      onClick={onClick}
      disabled={isDisabled}
      className={`
        relative
        ${baseStyles}
        ${variantStyles[variant]}
        ${sizeStyles[size]}
        ${isDisabled ? 'cursor-not-allowed' : 'cursor-pointer'}
        ${className}
      `}
      {...props}
    >
      <span className={`flex items-center justify-center ${loading ? 'opacity-0' : ''}`}>
        {children}
      </span>
      {loading && (
        <span className="absolute inset-0 flex items-center justify-center">
          <svg 
            className="animate-spin h-5 w-5 text-current" 
            xmlns="http://www.w3.org/2000/svg" 
            fill="none" 
            viewBox="0 0 24 24"
          >
            <circle 
              className="opacity-25" 
              cx="12" 
              cy="12" 
              r="10" 
              stroke="currentColor" 
              strokeWidth="4"
            />
            <path 
              className="opacity-75" 
              fill="currentColor" 
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
        </span>
      )}
    </button>
  );
}