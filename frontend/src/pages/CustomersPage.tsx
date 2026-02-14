import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { Layout } from "../components/Layout";
import { getCustomers, uploadCustomersCsv } from "../api/customers";
import type { Customer } from "../types/customers";

const SEGMENT_OPTIONS = [
  { value: "", label: "All segments" },
  { value: "smb", label: "SMB" },
  { value: "mid_market", label: "Mid-market" },
  { value: "enterprise", label: "Enterprise" },
];

export function CustomersPage() {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [segment, setSegment] = useState("");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadResult, setUploadResult] = useState<{ created: number; updated: number; skipped: number } | null>(null);

  useEffect(() => {
    setLoading(true);
    getCustomers({
      page,
      page_size: pageSize,
      segment: segment || undefined,
      search: search || undefined,
    })
      .then((res) => {
        setCustomers(res.data);
        setTotal(res.pagination.total);
        setTotalPages(res.pagination.total_pages);
      })
      .catch(() => setCustomers([]))
      .finally(() => setLoading(false));
  }, [page, pageSize, segment, search]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadError(null);
    setUploadResult(null);
    setUploading(true);
    uploadCustomersCsv(file)
      .then((result) => {
        setUploadResult(result);
        setPage(1);
        getCustomers({ page: 1, page_size: pageSize, segment: segment || undefined, search: search || undefined })
          .then((res) => {
            setCustomers(res.data);
            setTotal(res.pagination.total);
            setTotalPages(res.pagination.total_pages);
          })
          .catch(() => {});
      })
      .catch((err) => setUploadError(err.response?.data?.error?.message || err.message || "Upload failed"))
      .finally(() => setUploading(false));
    e.target.value = "";
  };

  return (
    <Layout>
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-semibold text-gray-800">Customers</h1>
        <label className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 cursor-pointer">
          <input type="file" accept=".csv" className="hidden" onChange={handleFileChange} disabled={uploading} />
          {uploading ? "Uploading…" : "Upload CSV"}
        </label>
      </div>
      {uploadError && <p className="mb-2 text-red-600 text-sm">{uploadError}</p>}
      {uploadResult && (
        <p className="mb-2 text-green-700 text-sm">
          Created: {uploadResult.created}, updated: {uploadResult.updated}, skipped: {uploadResult.skipped}
          {uploadResult.items_queued != null && uploadResult.items_queued > 0 && (
            <> · {uploadResult.items_queued} unmatched items queued for re-enrichment</>
          )}
        </p>
      )}
      <div className="mb-4 flex items-center gap-4">
        <select
          value={segment}
          onChange={(e) => { setSegment(e.target.value); setPage(1); }}
          className="rounded-md border border-gray-300 px-3 py-1.5 text-sm"
        >
          {SEGMENT_OPTIONS.map((o) => (
            <option key={o.value || "all"} value={o.value}>{o.label}</option>
          ))}
        </select>
        <input
          type="search"
          placeholder="Search domain or company..."
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          className="rounded-md border border-gray-300 px-3 py-1.5 text-sm w-64"
        />
      </div>
      {loading ? (
        <p className="text-gray-500">Loading...</p>
      ) : customers.length === 0 ? (
        <p className="text-gray-500">No customers. Upload a CSV with domain (and optional company name, segment).</p>
      ) : (
        <>
          <div className="overflow-x-auto border border-gray-200 rounded-lg">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Domain</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Company</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Segment</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {customers.map((c) => (
                  <tr key={c.id} className="hover:bg-gray-50">
                    <td className="px-4 py-2 text-sm font-medium text-gray-800">{c.domain}</td>
                    <td className="px-4 py-2 text-sm text-gray-600">{c.company_name || "—"}</td>
                    <td className="px-4 py-2 text-sm text-gray-600">{c.segment || "—"}</td>
                    <td className="px-4 py-2">
                      <Link to={`/customers/${c.id}`} className="text-blue-600 hover:underline text-sm">View</Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {totalPages > 1 && (
            <div className="mt-4 flex items-center gap-2">
              <button
                type="button"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1}
                className="rounded border border-gray-300 px-3 py-1 text-sm disabled:opacity-50"
              >
                Previous
              </button>
              <span className="text-sm text-gray-600">Page {page} of {totalPages} ({total} total)</span>
              <button
                type="button"
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
                className="rounded border border-gray-300 px-3 py-1 text-sm disabled:opacity-50"
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </Layout>
  );
}
