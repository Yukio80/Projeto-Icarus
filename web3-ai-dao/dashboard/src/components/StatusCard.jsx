export default function StatusCard({ title, value, subtitle, color }) {
  return (
    <div className="bg-icarus-card border border-icarus-border rounded-xl p-5">
      <p className="text-icarus-muted text-sm font-medium">{title}</p>
      <p className={`text-2xl font-bold mt-1 ${color || 'text-icarus-text'}`}>
        {value ?? '—'}
      </p>
      {subtitle && (
        <p className="text-icarus-muted text-xs mt-1">{subtitle}</p>
      )}
    </div>
  );
}
