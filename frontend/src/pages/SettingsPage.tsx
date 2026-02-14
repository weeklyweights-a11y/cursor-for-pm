import { useState } from "react";
import { Layout } from "../components/Layout";
import { SlackSettings } from "../components/SlackSettings";
import { ProductContextSettings } from "../components/ProductContextSettings";
import { ScoringSettings } from "../components/ScoringSettings";

export function SettingsPage() {
  const [error, setError] = useState<string | null>(null);

  return (
    <Layout>
      <h1 className="text-2xl font-semibold text-gray-800 mb-4">Settings</h1>
      <ProductContextSettings error={error} setError={setError} />
      <ScoringSettings />
      <SlackSettings />
    </Layout>
  );
}
