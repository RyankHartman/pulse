interface Props {
  label: string;
  names: string[];
  sql: Record<string, string>;
}

/** Shows the exact SQL files the pipeline ran, so every number can be traced to a query. */
export function SqlViewer({ label, names, sql }: Props) {
  const text = names.map((name) => `-- ${name}.sql\n${sql[name] ?? "(not found)"}`).join("\n\n");
  return (
    <details className="sql">
      <summary>{label}</summary>
      <pre>
        <code>{text}</code>
      </pre>
    </details>
  );
}
