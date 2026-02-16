import { useState, useEffect } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { useAuth } from "../context/authContext";
import { getReviewCount } from "../api/review";
import type { PageContext } from "../types/chat";
import { ChatFloatingButton } from "./ChatFloatingButton";
import { ChatSidebar } from "./ChatSidebar";

interface LayoutProps {
  children: React.ReactNode;
}

function usePageContext(): PageContext | null {
  const location = useLocation();
  const params = useParams<{ id?: string }>();
  const path = location.pathname;
  if (path.startsWith("/themes/") && params.id) return { type: "theme", id: params.id };
  if (path.startsWith("/feedback/") && params.id) return { type: "feedback", id: params.id };
  if (path.startsWith("/customers/") && params.id) return { type: "customer", id: params.id };
  return null;
}

export function Layout({ children }: LayoutProps) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [reviewCount, setReviewCount] = useState(0);
  const [chatOpen, setChatOpen] = useState(false);
  const pageContext = usePageContext();

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
      {chatOpen && (
        <ChatSidebar isOpen={true} onClose={() => setChatOpen(false)} pageContext={pageContext} />
      )}
      {!chatOpen && <ChatFloatingButton onClick={() => setChatOpen(true)} />}
    </div>
  );
}
