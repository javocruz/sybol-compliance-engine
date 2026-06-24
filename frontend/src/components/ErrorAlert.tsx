import './ErrorAlert.css';

interface ErrorAlertProps {
  message: string;
  title?: string;
}

export function ErrorAlert({ message, title = 'Analysis failed' }: ErrorAlertProps) {
  return (
    <div className="error-alert" role="alert">
      <strong>{title}</strong>
      <p>{message}</p>
    </div>
  );
}
