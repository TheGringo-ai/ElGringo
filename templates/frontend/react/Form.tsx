/**
 * Form Components
 * ===============
 * Reusable form components with validation using react-hook-form and zod.
 *
 * Dependencies:
 *   npm install react-hook-form @hookform/resolvers zod lucide-react
 *
 * Usage:
 *   <Form onSubmit={handleSubmit} schema={userSchema}>
 *     <FormField name="email" label="Email" type="email" />
 *     <FormField name="password" label="Password" type="password" />
 *     <SubmitButton>Sign In</SubmitButton>
 *   </Form>
 */

import React, { createContext, useContext } from 'react';
import { useForm, FormProvider, useFormContext, FieldValues, DefaultValues } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { AlertCircle, Check, Loader2, Eye, EyeOff } from 'lucide-react';

// ============================================================================
// FORM CONTEXT
// ============================================================================

interface FormContextValue {
  isSubmitting: boolean;
}

const FormContext = createContext<FormContextValue>({ isSubmitting: false });

// ============================================================================
// FORM WRAPPER
// ============================================================================

interface FormProps<T extends FieldValues> {
  children: React.ReactNode;
  onSubmit: (data: T) => Promise<void> | void;
  schema: z.ZodSchema<T>;
  defaultValues?: DefaultValues<T>;
  className?: string;
}

export function Form<T extends FieldValues>({
  children,
  onSubmit,
  schema,
  defaultValues,
  className = '',
}: FormProps<T>) {
  const methods = useForm<T>({
    resolver: zodResolver(schema),
    defaultValues,
  });

  const handleSubmit = methods.handleSubmit(async (data) => {
    await onSubmit(data);
  });

  return (
    <FormProvider {...methods}>
      <FormContext.Provider value={{ isSubmitting: methods.formState.isSubmitting }}>
        <form onSubmit={handleSubmit} className={`space-y-4 ${className}`}>
          {children}
        </form>
      </FormContext.Provider>
    </FormProvider>
  );
}

// ============================================================================
// FORM FIELD
// ============================================================================

interface FormFieldProps {
  name: string;
  label?: string;
  type?: 'text' | 'email' | 'password' | 'number' | 'tel' | 'url' | 'textarea';
  placeholder?: string;
  description?: string;
  required?: boolean;
  disabled?: boolean;
  className?: string;
  rows?: number;
}

export function FormField({
  name,
  label,
  type = 'text',
  placeholder,
  description,
  required = false,
  disabled = false,
  className = '',
  rows = 3,
}: FormFieldProps) {
  const { register, formState: { errors } } = useFormContext();
  const [showPassword, setShowPassword] = React.useState(false);
  const error = errors[name];

  const inputType = type === 'password' && showPassword ? 'text' : type;

  const baseClasses = `
    w-full px-3 py-2 border rounded-lg transition-colors
    focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
    disabled:bg-gray-100 disabled:cursor-not-allowed
    ${error ? 'border-red-500' : 'border-gray-300'}
  `;

  return (
    <div className={`space-y-1 ${className}`}>
      {label && (
        <label htmlFor={name} className="block text-sm font-medium text-gray-700">
          {label}
          {required && <span className="text-red-500 ml-1">*</span>}
        </label>
      )}

      <div className="relative">
        {type === 'textarea' ? (
          <textarea
            id={name}
            {...register(name)}
            placeholder={placeholder}
            disabled={disabled}
            rows={rows}
            className={baseClasses}
          />
        ) : (
          <input
            id={name}
            type={inputType}
            {...register(name, { valueAsNumber: type === 'number' })}
            placeholder={placeholder}
            disabled={disabled}
            className={`${baseClasses} ${type === 'password' ? 'pr-10' : ''}`}
          />
        )}

        {type === 'password' && (
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
          >
            {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
          </button>
        )}
      </div>

      {description && !error && (
        <p className="text-sm text-gray-500">{description}</p>
      )}

      {error && (
        <p className="text-sm text-red-500 flex items-center gap-1">
          <AlertCircle className="w-4 h-4" />
          {error.message as string}
        </p>
      )}
    </div>
  );
}

// ============================================================================
// SELECT FIELD
// ============================================================================

interface SelectOption {
  value: string;
  label: string;
}

interface SelectFieldProps {
  name: string;
  label?: string;
  options: SelectOption[];
  placeholder?: string;
  required?: boolean;
  disabled?: boolean;
  className?: string;
}

export function SelectField({
  name,
  label,
  options,
  placeholder = 'Select an option',
  required = false,
  disabled = false,
  className = '',
}: SelectFieldProps) {
  const { register, formState: { errors } } = useFormContext();
  const error = errors[name];

  return (
    <div className={`space-y-1 ${className}`}>
      {label && (
        <label htmlFor={name} className="block text-sm font-medium text-gray-700">
          {label}
          {required && <span className="text-red-500 ml-1">*</span>}
        </label>
      )}

      <select
        id={name}
        {...register(name)}
        disabled={disabled}
        className={`
          w-full px-3 py-2 border rounded-lg transition-colors
          focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
          disabled:bg-gray-100 disabled:cursor-not-allowed
          ${error ? 'border-red-500' : 'border-gray-300'}
        `}
      >
        <option value="">{placeholder}</option>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>

      {error && (
        <p className="text-sm text-red-500 flex items-center gap-1">
          <AlertCircle className="w-4 h-4" />
          {error.message as string}
        </p>
      )}
    </div>
  );
}

// ============================================================================
// CHECKBOX FIELD
// ============================================================================

interface CheckboxFieldProps {
  name: string;
  label: string;
  description?: string;
  disabled?: boolean;
  className?: string;
}

export function CheckboxField({
  name,
  label,
  description,
  disabled = false,
  className = '',
}: CheckboxFieldProps) {
  const { register } = useFormContext();

  return (
    <div className={`flex items-start gap-3 ${className}`}>
      <input
        id={name}
        type="checkbox"
        {...register(name)}
        disabled={disabled}
        className="mt-1 h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
      />
      <div>
        <label htmlFor={name} className="text-sm font-medium text-gray-700">
          {label}
        </label>
        {description && <p className="text-sm text-gray-500">{description}</p>}
      </div>
    </div>
  );
}

// ============================================================================
// SUBMIT BUTTON
// ============================================================================

interface SubmitButtonProps {
  children: React.ReactNode;
  className?: string;
  variant?: 'primary' | 'secondary' | 'danger';
}

export function SubmitButton({
  children,
  className = '',
  variant = 'primary',
}: SubmitButtonProps) {
  const { isSubmitting } = useContext(FormContext);

  const variants = {
    primary: 'bg-blue-600 hover:bg-blue-700 text-white',
    secondary: 'bg-gray-200 hover:bg-gray-300 text-gray-800',
    danger: 'bg-red-600 hover:bg-red-700 text-white',
  };

  return (
    <button
      type="submit"
      disabled={isSubmitting}
      className={`
        px-4 py-2 rounded-lg font-medium transition-colors
        disabled:opacity-50 disabled:cursor-not-allowed
        flex items-center justify-center gap-2
        ${variants[variant]}
        ${className}
      `}
    >
      {isSubmitting && <Loader2 className="w-4 h-4 animate-spin" />}
      {children}
    </button>
  );
}

// ============================================================================
// EXAMPLE SCHEMAS
// ============================================================================

export const loginSchema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
  remember: z.boolean().optional(),
});

export const registerSchema = z.object({
  name: z.string().min(2, 'Name must be at least 2 characters'),
  email: z.string().email('Invalid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
  confirmPassword: z.string(),
  terms: z.boolean().refine((val) => val === true, 'You must accept the terms'),
}).refine((data) => data.password === data.confirmPassword, {
  message: "Passwords don't match",
  path: ['confirmPassword'],
});

export const contactSchema = z.object({
  name: z.string().min(2, 'Name is required'),
  email: z.string().email('Invalid email'),
  subject: z.string().min(1, 'Subject is required'),
  message: z.string().min(10, 'Message must be at least 10 characters'),
});

// ============================================================================
// EXAMPLE USAGE
// ============================================================================

export function LoginFormExample() {
  const handleSubmit = async (data: z.infer<typeof loginSchema>) => {
    console.log('Login:', data);
    await new Promise((resolve) => setTimeout(resolve, 1000));
  };

  return (
    <div className="max-w-md mx-auto p-6">
      <h2 className="text-2xl font-bold mb-6">Sign In</h2>
      <Form onSubmit={handleSubmit} schema={loginSchema}>
        <FormField name="email" label="Email" type="email" required />
        <FormField name="password" label="Password" type="password" required />
        <CheckboxField name="remember" label="Remember me" />
        <SubmitButton className="w-full">Sign In</SubmitButton>
      </Form>
    </div>
  );
}
