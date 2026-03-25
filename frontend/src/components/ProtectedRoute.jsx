import { Navigate } from "react-router-dom";
import { getToken } from "../lib/auth";

export default function ProtectedRoute({ children }) {
  return getToken() ? children : <Navigate to="/" replace />;
}
