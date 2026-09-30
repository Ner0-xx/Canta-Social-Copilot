import { Plus, X } from "lucide-react";
import { type KeyboardEvent, useState } from "react";

interface TagInputProps {
  id: string;
  label: string;
  values: string[];
  placeholder?: string;
  onChange: (values: string[]) => void;
}

export function TagInput({
  id,
  label,
  values,
  placeholder,
  onChange,
}: TagInputProps) {
  const [value, setValue] = useState("");

  const addValue = () => {
    const next = value.trim();
    if (!next || values.some((item) => item.toLowerCase() === next.toLowerCase())) {
      return;
    }
    onChange([...values, next]);
    setValue("");
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter" || event.key === ",") {
      event.preventDefault();
      addValue();
    }
  };

  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      {values.length > 0 && (
        <div className="tag-list">
          {values.map((item) => (
            <span className="tag" key={item}>
              {item}
              <button
                type="button"
                className="tag-remove"
                onClick={() => onChange(values.filter((valueItem) => valueItem !== item))}
                aria-label={`Remove ${item}`}
                title={`Remove ${item}`}
              >
                <X size={13} />
              </button>
            </span>
          ))}
        </div>
      )}
      <div className="input-action">
        <input
          id={id}
          value={value}
          placeholder={placeholder}
          onChange={(event) => setValue(event.target.value)}
          onKeyDown={handleKeyDown}
        />
        <button
          className="icon-button"
          type="button"
          onClick={addValue}
          aria-label={`Add ${label.toLowerCase()}`}
          title={`Add ${label.toLowerCase()}`}
        >
          <Plus size={17} />
        </button>
      </div>
    </div>
  );
}

