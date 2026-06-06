import { toast } from "sonner";

interface AxiosLikeError {
  response?: { data?: { detail?: string } };
  message?: string;
}

function extractMessage(e: unknown, fallback: string): string {
  const ae = e as AxiosLikeError;
  return (
    ae?.response?.data?.detail ??
    ae?.message ??
    fallback
  );
}

export function showError(e: unknown, fallback = "Something went wrong"): void {
  toast.error(extractMessage(e, fallback));
}

export function showSuccess(message: string): void {
  toast.success(message);
}

export { toast };
