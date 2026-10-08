import { clsx } from 'clsx';

export interface PasswordStrengthProps {
  password: string;
}

function calculateStrength(password: string): 'weak' | 'ok' | 'strong' {
  if (password.length < 6) return 'weak';
  
  let score = 0;
  if (password.length >= 8) score++;
  if (/[a-z]/.test(password) && /[A-Z]/.test(password)) score++;
  if (/\d/.test(password)) score++;
  if (/[^a-zA-Z0-9]/.test(password)) score++;
  
  if (score <= 1) return 'weak';
  if (score <= 2) return 'ok';
  return 'strong';
}

export function PasswordStrength({ password }: PasswordStrengthProps) {
  if (!password) return null;
  
  const strength = calculateStrength(password);
  const segments = 4;
  const activeSegments = strength === 'weak' ? 1 : strength === 'ok' ? 2 : 4;
  
  const colors = {
    weak: 'bg-red-500',
    ok: 'bg-amber-500',
    strong: 'bg-green-500',
  };
  
  const labels = {
    weak: 'Weak',
    ok: 'Good',
    strong: 'Strong',
  };
  
  return (
    <div className="mt-2">
      <div className="flex gap-1 mb-1">
        {Array.from({ length: segments }).map((_, i) => (
          <div
            key={i}
            className={clsx(
              'h-1 flex-1 rounded-full transition-colors',
              i < activeSegments ? colors[strength] : 'bg-gray-200'
            )}
          />
        ))}
      </div>
      <p className="text-xs text-text-secondary">
        Password strength: <span className="font-medium">{labels[strength]}</span>
      </p>
    </div>
  );
}
