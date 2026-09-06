// components/ui/select.tsx
import React, { useState } from 'react';
import { ChevronDown } from 'lucide-react';
import { cn } from './utils';

interface SelectProps {
  children: React.ReactNode;
}

interface SelectTriggerProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  children: React.ReactNode;
}

interface SelectContentProps {
  children: React.ReactNode;
}

interface SelectItemProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  value: string;
  children: React.ReactNode;
}

export function Select({ children }: SelectProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [selectedValue, setSelectedValue] = useState('');

  return (
    <div className="relative">
      {React.Children.map(children, child => {
        if (React.isValidElement(child)) {
          return React.cloneElement(child, {
            isOpen,
            setIsOpen,
            selectedValue,
            setSelectedValue
          } as any);
        }
        return child;
      })}
    </div>
  );
}

export function SelectTrigger({ 
  className, 
  children, 
  isOpen, 
  setIsOpen,
  ...props 
}: SelectTriggerProps & { isOpen?: boolean; setIsOpen?: (open: boolean) => void }) {
  return (
    <button
      type="button"
      className={cn(
        'flex h-10 w-full items-center justify-between rounded-md border border-gray-300 bg-white px-3 py-2 text-sm placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
        className
      )}
      onClick={() => setIsOpen?.(!isOpen)}
      {...props}
    >
      <span>{children}</span>
      <ChevronDown className="h-4 w-4 text-gray-500" />
    </button>
  );
}

export function SelectContent({ 
  children, 
  isOpen, 
  setIsOpen,
  selectedValue,
  setSelectedValue
}: SelectContentProps & { 
  isOpen?: boolean; 
  setIsOpen?: (open: boolean) => void;
  selectedValue?: string;
  setSelectedValue?: (value: string) => void;
}) {
  if (!isOpen) return null;

  return (
    <div className="absolute z-50 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg">
      <div className="py-1">
        {React.Children.map(children, child => {
          if (React.isValidElement(child)) {
            return React.cloneElement(child, {
              selectedValue,
              setSelectedValue,
              setIsOpen
            } as any);
          }
          return child;
        })}
      </div>
    </div>
  );
}

export function SelectItem({ 
  className, 
  value, 
  children, 
  selectedValue,
  setSelectedValue,
  setIsOpen,
  ...props 
}: SelectItemProps & { 
  selectedValue?: string; 
  setSelectedValue?: (value: string) => void;
  setIsOpen?: (open: boolean) => void;
}) {
  return (
    <button
      type="button"
      className={cn(
        'w-full text-left px-3 py-2 text-sm hover:bg-gray-100 focus:bg-gray-100 focus:outline-none',
        className
      )}
      onClick={() => {
        setSelectedValue?.(value);
        setIsOpen?.(false);
      }}
      {...props}
    >
      {children}
    </button>
  );
}