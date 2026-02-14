import { useEffect, useState } from "react";
import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../context/authContext";
import { getProductContext } from "../api/productContext";
import { LoadingSpinner } from "./LoadingSpinner";

export function PrivateRoute() {
  const { user, isLoading } = useAuth();
  const location = useLocation();
  const [checkingContext, setCheckingContext] = useState(false);
  const [hasContext, setHasContext] = useState<boolean | null>(null);

  const isOnboarding = location.pathname === "/onboarding" || location.pathname.startsWith("/onboarding/");

  useEffect(() => {
    if (!user || isOnboarding) {
      setHasContext(isOnboarding ? true : null);
      return;
    }
    setCheckingContext(true);
    getProductContext()
      .then((ctx) => setHasContext(ctx != null))
      .catch(() => setHasContext(false))
      .finally(() => setCheckingContext(false));
  }, [user, isOnboarding]);

  if (isLoading) {
    return <LoadingSpinner />;
  }
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  if (isOnboarding) {
    return <Outlet />;
  }
  if (checkingContext || hasContext === null) {
    return <LoadingSpinner />;
  }
  if (!hasContext) {
    return <Navigate to="/onboarding" replace />;
  }
  return <Outlet />;
}
