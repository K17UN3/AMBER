import type { Category } from "../types";

type CategorySelectProps = {
  categories: Category[];
  value: string;
  onChange: (categoryName: string) => void;
  disabled?: boolean;
};

export default function CategorySelect({
  categories,
  value,
  onChange,
  disabled = false,
}: CategorySelectProps) {
  return (
    <select
      value={value}
      onChange={(event) => onChange(event.target.value)}
      disabled={disabled || categories.length === 0}
    >
      {categories.length === 0 ? <option value="その他">その他</option> : null}
      {categories.map((category) => (
        <option key={category.id} value={category.name}>
          {category.name}
        </option>
      ))}
    </select>
  );
}
