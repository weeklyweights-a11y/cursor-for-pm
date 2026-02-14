import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/authContext";
import { getReviewCount } from "../api/review";

interface LayoutProps {
  children: React.ReactNode;
}

export function Layout({ children }: LayoutProps) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [reviewCount, setReviewCount] = useState(0);

  useEffect(() => {
    getReviewCount()
      .then(setReviewCount)
      .catch(() => setReviewCount(0));
  }, []);

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div className="flex h-screen bg-gray-50">
      <aside className="w-[250px] bg-white border-r border-gray-200 flex flex-col">
        <div className="p-4 border-b border-gray-200">
          <span className="font-semibold text-gray-800">Cursor for PMs</span>
        </div>
        <nav className="p-2 flex-1">
          <Link
            to="/priorities"
            className="block px-3 py-2 rounded-md text-gray-700 hover:bg-gray-100"
          >
            Priorities
          </Link>
          <Link
            to="/dashboard"
            className="block px-3 py-2 rounded-md text-gray-700 hover:bg-gray-100"
          >
            Dashboard
          </Link>
          <Link
            to="/feedback"
            className="block px-3 py-2 rounded-md text-gray-700 hover:bg-gray-100"
          >
            Feedback
          </Link>
          <Link
            to="/customers"
            className="block px-3 py-2 rounded-md text-gray-700 hover:bg-gray-100"
          >
            Customers
          </Link>
          <Link
            to="/review-queue"
            className="block px-3 py-2 rounded-md text-gray-700 hover:bg-gray-100 flex items-center justify-between"
          >
            Review queue
            {reviewCount > 0 && (
              <span className="bg-amber-500 text-white text-xs font-medium rounded-full px-2 py-0.5">
                {reviewCount}
              </span>
            )}
          </Link>
          <Link
            to="/settings"
            className="block px-3 py-2 rounded-md text-gray-700 hover:bg-gray-100"
          >
            Settings
          </Link>
        </nav>
        <div className="p-4 border-t border-gray-200">
          <p className="text-sm text-gray-600 truncate">{user?.name}</p>
          <button
            type="button"
            onClick={handleLogout}
            className="mt-2 text-sm text-blue-600 hover:text-blue-800"
          >
            Log out
          </button>
        </div>
      </aside>
      <main className="flex-1 overflow-auto p-6 flex justify-center">
        <div className="w-full max-w-5xl">{children}</div>
      </main>
      <aside className="w-[320px] bg-gray-100 border-l border-gray-200 flex flex-col p-4">
        <h3 className="font-medium text-gray-700 mb-2">AI Assistant</h3>
        <p className="text-sm text-gray-500 flex-1 flex items-center justify-center">
          Chat will be available soon
        </p>
      </aside>
    </div>
  );
}
