import { useNavigate } from "react-router-dom";
import { Layout } from "../components/Layout";
import { ManualFeedbackForm } from "../components/ManualFeedbackForm";

export function AddManualFeedbackPage() {
  const navigate = useNavigate();
  return (
    <Layout>
      <h1 className="text-2xl font-semibold text-gray-800 mb-4">Add feedback manually</h1>
      <ManualFeedbackForm
        onSuccess={() => navigate("/feedback")}
        onCancel={() => navigate("/feedback")}
      />
    </Layout>
  );
}
