import type { LLMModel } from "../api/models";
import { formatPrice } from "../lib/modelChoice";

interface Props {
  models: LLMModel[];
  value: string | undefined;
  onChange: (id: string) => void;
  disabled?: boolean;
  className?: string;
}

export default function ModelSelect({ models, value, onChange, disabled, className }: Props) {
  const current = models.find((m) => m.id === value);
  return (
    <select
      name="model"
      value={value ?? ""}
      onChange={(e) => onChange(e.target.value)}
      className={className}
      disabled={disabled || models.length === 0}
      title={current ? formatPrice(current) : undefined}
    >
      {models.map((m) => (
        <option key={m.id} value={m.id} disabled={!m.available}>
          {m.label}
          {m.is_default ? " (défaut)" : ""}
          {m.available ? ` — ${m.input_price.toLocaleString("fr-FR")} $ / ${m.output_price.toLocaleString("fr-FR")} $` : " — clé API manquante"}
        </option>
      ))}
    </select>
  );
}
