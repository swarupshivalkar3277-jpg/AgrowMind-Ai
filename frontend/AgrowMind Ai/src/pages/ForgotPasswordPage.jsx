import { Link, useNavigate } from "react-router-dom";

import Login from "./Login";

export default function ForgotPasswordPage() {
  const navigate = useNavigate();
  return (
    <div className="forgotShell">
      <Login onHome={() => navigate("/login")} onSwitch={() => navigate("/register")} startForgot />
      <Link className="textButton" to="/login">Back to login</Link>
    </div>
  );
}
