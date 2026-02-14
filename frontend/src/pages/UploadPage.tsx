import { useState, useCallback, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Layout } from "../components/Layout";
import { uploadFeedbackCsv } from "../api/feedback";
import { getBatch } from "../api/batches";

const POLL_INTERVAL_MS = 2000;

export function UploadPage() {
  const navigate = useNavigate();
  const [dragging, setDragging] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [batchId, setBatchId] = useState<string | null>(null);
  const [progress, setProgress] = useState<{ total: number; processed: number; status: string } | null>(null);

  useEffect(() => {
    if (!batchId) return;
    const poll = async () => {
      try {
        const b = await getBatch(batchId);
        setProgress({
          total: b.total_rows,
          processed: b.processed_rows,
          status: b.status,
        });
        if (b.status === "completed" || b.status === "failed") {
          setBatchId(null);
          if (b.status === "completed") setTimeout(() => navigate("/feedback"), 1500);
        }
      } catch {
        setBatchId(null);
      }
    };
    poll();
    const interval = setInterval(poll, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [batchId, navigate]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files?.[0];
    if (f?.name.toLowerCase().endsWith(".csv")) setFile(f);
    else setError("Please select a .csv file.");
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
  }, []);

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f?.name.toLowerCase().endsWith(".csv")) {
      setFile(f);
      setError(null);
    } else if (f) setError("Please select a .csv file.");
  };

  const handleUpload = async () => {
    if (!file) return;
    setError(null);
    setUploading(true);
    try {
      const result = await uploadFeedbackCsv(file);
      if (result.sync) {
        navigate("/feedback");
        return;
      }
      setProgress({
        total: result.batch.total_rows,
        processed: result.batch.processed_rows,
        status: result.batch.status,
      });
      setBatchId(result.batch.id);
    } catch (err: unknown) {
      const msg =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { data?: { error?: { message?: string }; detail?: string } } }).response?.data?.error?.message ||
            (err as { response?: { data?: { detail?: string } } }).response?.data?.detail ||
            "Upload failed"
          : "Upload failed";
      setError(msg);
    } finally {
      setUploading(false);
    }
  };

  return (
    <Layout>
      <h1 className="text-2xl font-semibold text-gray-800 mb-4">Upload CSV</h1>
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        className={`border-2 border-dashed rounded-lg p-8 text-center ${
          dragging ? "border-blue-500 bg-blue-50" : "border-gray-300 bg-gray-50"
        }`}
      >
        <input
          type="file"
          accept=".csv"
          onChange={handleFileInput}
          className="hidden"
          id="csv-upload"
        />
        <label htmlFor="csv-upload" className="cursor-pointer">
          {file ? (
            <p className="text-gray-700">{file.name} ({(file.size / 1024).toFixed(1)} KB)</p>
          ) : (
            <p className="text-gray-600">Drag and drop a CSV file here, or click to select</p>
          )}
        </label>
      </div>
      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
      <div className="mt-4 flex gap-2">
        <button
          type="button"
          onClick={handleUpload}
          disabled={!file || uploading}
          className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {uploading ? "Uploading..." : "Upload"}
        </button>
        <button
          type="button"
          onClick={() => navigate("/feedback")}
          className="rounded-md border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
        >
          Cancel
        </button>
      </div>
      {progress && batchId && (
        <div className="mt-6">
          <p className="text-sm text-gray-600 mb-2">
            Processing {progress.processed} of {progress.total} items... ({progress.status})
          </p>
          <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-blue-600 transition-all"
              style={{ width: `${progress.total ? (100 * progress.processed) / progress.total : 0}%` }}
            />
          </div>
          {progress.status === "completed" && (
            <p className="mt-2 text-sm text-green-600">Done! Redirecting to feedback list...</p>
          )}
          {progress.status === "failed" && (
            <p className="mt-2 text-sm text-red-600">Processing failed. Check batch details.</p>
          )}
        </div>
      )}
    </Layout>
  );
}
