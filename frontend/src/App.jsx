import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { isAuthed } from "./api/client";
import NavBar from "./components/NavBar";
import AIChat from "./components/AIChat";
import Home from "./pages/Home";
import Login from "./pages/Login";
import StockDetails from "./pages/StockDetails";
import Watchlist from "./pages/Watchlist";

function Protected({ children }) { return isAuthed() ? children : <Navigate to="/login" replace />; }
function Layout({ children }) { return <div className="min-h-screen bg-paper"><div className="max-w-2xl mx-auto px-4"><NavBar /></div>{children}<AIChat /></div>; }
function Page({ children }) { return <Protected><Layout>{children}</Layout></Protected>; }
export default function App() { return <BrowserRouter><Routes><Route path="/login" element={<Login />} /><Route path="/" element={<Page><Home /></Page>} /><Route path="/watchlist" element={<Page><Watchlist /></Page>} /><Route path="/stocks/:symbol" element={<Page><StockDetails /></Page>} /><Route path="*" element={<Navigate to="/" replace />} /></Routes></BrowserRouter>; }
