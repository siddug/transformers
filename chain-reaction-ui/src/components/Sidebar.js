'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

const menuItems = [
  {
    name: 'Translator',
    path: '/translator',
    description: 'Translate text to different languages'
  },
  {
    name: 'Translator Chain',
    path: '/translator-chain',
    description: 'Chain multiple translations'
  }
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <div className="w-64 bg-gray-50 h-screen fixed left-0 top-0">
      <div className="p-6">
        <h1 className="text-2xl text-gray-900 font-bold mb-8">Chain Reaction</h1>
        
        <nav className="space-y-1">
          {menuItems.map((item) => {
            const isActive = pathname === item.path;
            return (
              <Link
                key={item.path}
                href={item.path}
                className={`block py-1 px-2 text-sm rounded-lg transition-colors ${
                  isActive
                    ? 'bg-gray-200 text-gray-900'
                    : 'hover:bg-gray-200 bg-gray-50 text-gray-900'
                }`}
              >
                <div className="font-medium">{item.name}</div>
              </Link>
            );
          })}
        </nav>
      </div>
    </div>
  );
}